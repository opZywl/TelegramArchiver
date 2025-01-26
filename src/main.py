"""
 * This file is part of Telegram Archiver downloader (https://github.dev/opZywl/TelegramArchiver)
 *
 *
 * Telegram Archiver downloader is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Telegram Archiver downloader is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Telegram Archiver downloader. If not, see <https://www.gnu.org/licenses/>.
 
"""
import asyncio
import os
import hashlib
import logging
from dotenv import load_dotenv
from colorama import Fore, Style
from tqdm.asyncio import tqdm
from telethon import TelegramClient
from telethon.tl.types import (
    DocumentAttributeFilename,
    InputMessagesFilterVideo,
    InputMessagesFilterPhotos,
    InputMessagesFilterDocument,
    Channel,
    Chat,
)
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty
from telethon.tl.functions.users import GetFullUserRequest
from telethon.errors import FloodWaitError

# Carregar variáveis de ambiente
load_dotenv()

# Obter valores de .env
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
session_name = os.getenv("SESSION_NAME", "default_session")
batch_size = int(os.getenv("BATCH_SIZE", 5))
download_path_base = r"C:\Users\lucas\Desktop\zy\Telegram\Downloads"

semaphore = asyncio.Semaphore(20)

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def listar_canais_disponiveis(client):
    logger.info("Buscando canais e grupos disponíveis...")
    print(f"{Fore.YELLOW}Buscando canais e grupos disponíveis...{Style.RESET_ALL}")

    last_date = None
    chunk_size = 200
    all_dialogs = []

    while True:
        try:
            result = await client(
                GetDialogsRequest(
                    offset_date=last_date,
                    offset_id=0,
                    offset_peer=InputPeerEmpty(),
                    limit=chunk_size,
                    hash=0,
                )
            )
            if not result.dialogs:
                break

            for dialog, entity in zip(result.dialogs, result.chats):
                if isinstance(entity, (Channel, Chat)):
                    all_dialogs.append(entity)
                elif not isinstance(entity, InputPeerEmpty):
                    # Se for um usuário, tenta obter informações detalhadas
                    try:
                        user_full = await client(GetFullUserRequest(entity.id))
                        if user_full and user_full.user:
                            all_dialogs.append(user_full.user)
                    except Exception as e:
                        logger.error(f"ERRO: Não foi possível buscar informações completas do usuário: {e}")
                        print(
                            f"{Fore.RED}ERRO: Não foi possível buscar informações completas do usuário: {e}{Style.RESET_ALL}"
                        )

            last_date = result.messages[-1].date if result.messages else None

            if len(result.dialogs) < chunk_size:
                break

        except Exception as e:
            logger.error(f"ERRO: Falha ao buscar diálogos: {e}")
            print(f"{Fore.RED}ERRO: Falha ao buscar diálogos: {e}{Style.RESET_ALL}")
            return []

    if all_dialogs:
        print(f"{Fore.GREEN}Canais, grupos e usuários disponíveis:{Style.RESET_ALL}")
        for i, entity in enumerate(all_dialogs):
            if hasattr(entity, "title"):
                print(
                    f"{i + 1}. {Fore.BLUE}{entity.title}{Style.RESET_ALL} (ID: {entity.id})"
                )
            elif hasattr(entity, "first_name") and hasattr(entity, "last_name"):
                print(
                    f"{i + 1}. {Fore.BLUE}{entity.first_name} {entity.last_name}{Style.RESET_ALL} (ID: {entity.id})"
                )
            else:
                print(f"{i + 1}. {Fore.BLUE}ID do Usuário: {entity.id}{Style.RESET_ALL}")

    else:
        print(f"{Fore.RED}Nenhum canal, grupo ou usuário encontrado.{Style.RESET_ALL}")
    return all_dialogs


async def calcular_hash_arquivo(file_path):
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        logger.error(f"ERRO: Falha ao calcular hash do arquivo {file_path}: {e}")
        print(f"{Fore.RED}ERRO: Falha ao calcular hash do arquivo {file_path}: {e}{Style.RESET_ALL}")
        return None


async def baixar_arquivo(message, folder_name, global_progress_bar, channel, downloaded_hashes, file_index,
                         total_files):
    async with semaphore:
        file_path = None
        try:
            # Obter o tamanho do arquivo
            file_size = 0
            if message.video:
                file_size = message.video.size
            elif message.document:
                file_size = message.document.size

            if file_size > 6 * 1024 * 1024 * 1024:
                print(
                    f"{Fore.YELLOW}AVISO: Arquivo {file_index}/{total_files} - {message.id} é maior que 6GB ({file_size} bytes), pulando download.{Style.RESET_ALL}")
                logger.info(
                    f"AVISO: Arquivo {file_index}/{total_files} - {message.id} é maior que 6GB, pulando download.")
                return

            # Extrair info do canal para logging
            if hasattr(channel, "title"):
                channel_info = f"Canal: {channel.title} (ID: {channel.id})"
            elif hasattr(channel, "first_name"):
                channel_info = f"Usuário: {channel.first_name} {channel.last_name} (ID: {channel.id})"
            else:
                channel_info = f"ID do Usuário: {channel.id}"

            # Inicializar a barra de progresso
            progress_bar = tqdm(
                total=file_size,
                desc=f"Baixando {message.id}",
                ncols=100,
                unit="B",
                unit_scale=True,
                leave=False,
                bar_format=(
                        "{l_bar}%s{bar}%s| {n_fmt}/{total_fmt} {unit} "
                        "| Tempo: {elapsed}/{remaining} | {rate_fmt}"
                        % (Fore.BLUE, Style.RESET_ALL)
                ),
            )

            # Baixar a mídia com progresso
            file_path = await message.download_media(
                file=f"{download_path_base}/{folder_name}/",
                progress_callback=lambda current, total: (
                    progress_bar.update(current - progress_bar.n),
                    global_progress_bar.update(current - global_progress_bar.n),
                ) if total else None,
            )

            # Após o download, mudar a cor para verde
            progress_bar.bar_format = (
                    "{l_bar}%s{bar}%s| {n_fmt}/{total_fmt} {unit} "
                    "| Tempo: {elapsed}/{rate_fmt}" % (Fore.GREEN, Style.RESET_ALL)
            )
            progress_bar.set_description(f"Finalizado {message.id}")
            progress_bar.n = progress_bar.total
            progress_bar.update(0)

            if file_path:
                file_hash = await calcular_hash_arquivo(file_path)
                if file_hash:
                    if file_hash in downloaded_hashes:
                        os.remove(file_path)
                        print(
                            f"{Fore.YELLOW}AVISO: Arquivo {file_index}/{total_files} - {message.id} de {channel_info} é duplicado, pulando download.{Style.RESET_ALL}")
                        logger.info(
                            f"AVISO: Arquivo {file_index}/{total_files} - {message.id} de {channel_info} é duplicado, pulando download.")
                        return
                    else:
                        downloaded_hashes[file_hash] = True
                        if await verificar_integridade_arquivo(
                                file_path,
                                message.document.size if message.document else message.video.size,
                        ):
                            print(
                                f"{Fore.GREEN}INFO: Arquivo {file_index}/{total_files} - {message.id} de {channel_info} baixado com sucesso!{Style.RESET_ALL}")
                            logger.info(
                                f"INFO: Arquivo {file_index}/{total_files} - {message.id} de {channel_info} baixado com sucesso!")
                        else:
                            print(
                                f"{Fore.RED}ERRO: Arquivo {file_index}/{total_files} - {message.id} de {channel_info} baixado mas verificação de integridade falhou!{Style.RESET_ALL}")
                            logger.error(
                                f"ERRO: Arquivo {file_index}/{total_files} - {message.id} de {channel_info} baixado mas verificação de integridade falhou!")
                else:
                    print(
                        f"{Fore.RED}ERRO: Arquivo {file_index}/{total_files} - {message.id} de {channel_info} - Falha ao calcular hash, pulando verificação de duplicados.{Style.RESET_ALL}")
                    logger.error(
                        f"ERRO: Arquivo {file_index}/{total_files} - {message.id} de {channel_info} - Falha ao calcular hash, pulando verificação de duplicados.")
            else:
                print(
                    f"{Fore.RED}ERRO: Arquivo {file_index}/{total_files} - {message.id} de {channel_info} - Falha ao baixar arquivo {message.id}{Style.RESET_ALL}")
                logger.error(
                    f"ERRO: Arquivo {file_index}/{total_files} - {message.id} de {channel_info} - Falha ao baixar arquivo {message.id}")

        except FloodWaitError as e:
            logger.error(f"Flood wait: {e}. Aguardando {e.seconds} segundos.")
            print(f"{Fore.RED}Flood wait: {e}. Aguardando {e.seconds} segundos.{Style.RESET_ALL}")
            await asyncio.sleep(e.seconds)
            raise  # Re-raise para ser tratado na funcao baixar_todas_midias
        except Exception as e:
            logger.error(f"ERRO: Falha ao baixar mídia de {channel_info}: {e}")
            print(f"{Fore.RED}ERRO: Falha ao baixar mídia de {channel_info}: {e}{Style.RESET_ALL}")


async def verificar_integridade_arquivo(file_path, expected_size):
    try:
        actual_size = os.path.getsize(file_path)
        return actual_size == expected_size
    except Exception as e:
        logger.error(f"ERRO: Falha durante a verificação do tamanho do arquivo: {e}")
        print(f"{Fore.RED}ERRO: Falha durante a verificação do tamanho do arquivo: {e}{Style.RESET_ALL}")
        return False


async def baixar_todas_midias(client, channel):
    if hasattr(channel, "title"):
        folder_name = channel.title
    elif hasattr(channel, "first_name"):
        folder_name = f"{channel.first_name} {channel.last_name}"
    else:
        folder_name = f"ID do Usuário: {channel.id}"

    download_path = os.path.join(download_path_base, folder_name)
    os.makedirs(download_path, exist_ok=True)

    print(f"{Fore.YELLOW}Buscando todas as mensagens com mídia...{Style.RESET_ALL}")
    logger.info(f"Buscando todas as mensagens com mídia para {folder_name}")

    all_messages = []
    offset_id = 0

    downloaded_hashes = {}
    while True:
        try:
            media_messages = await client.get_messages(
                channel, limit=100, offset_id=offset_id
            )
            if not media_messages:
                break
            all_messages.extend([msg for msg in media_messages if msg.media])
            offset_id = media_messages[-1].id

        except Exception as e:
            logger.error(f"ERRO: Falha ao buscar mensagens: {e}")
            print(f"{Fore.RED}ERRO: Falha ao buscar mensagens: {e}{Style.RESET_ALL}")
            break

    print(f"Foram encontradas {len(all_messages)} mensagens com mídia em ", end="")
    if hasattr(channel, "title"):
        print(f"canal {channel.title}.")
    elif hasattr(channel, "first_name"):
        print(f"usuário {channel.first_name} {channel.last_name}.")
    else:
        print(f"ID do usuário: {channel.id}")

    print(f"{Fore.YELLOW}---------------------------------------------------------------------{Style.RESET_ALL}")

    if all_messages:
        total_size = sum(
            msg.video.size if msg.video else msg.document.size
            for msg in all_messages
            if msg.video or msg.document
        )
        print(
            f"{Fore.YELLOW}Iniciando o download de {len(all_messages)} arquivos de mídia, tamanho total: {total_size} bytes...{Style.RESET_ALL}"
        )
        logger.info(f"Iniciando o download de {len(all_messages)} arquivos de mídia.")

        file_index = 0
        total_files = len(all_messages)

        with tqdm(
                total=total_size,
                desc="Progresso Total",
                unit="B",
                unit_scale=True,
                ncols=100,
                bar_format=(
                        "{l_bar}%s{bar}%s| {n_fmt}/{total_fmt} {unit} "
                        "| Tempo: {elapsed}/{remaining} | {rate_fmt}"
                        % (Fore.MAGENTA, Style.RESET_ALL)
                ),
        ) as global_progress_bar:

            batch_size = 20  # Define o tamanho do lote (voce pode ajustar)
            for i in range(0, len(all_messages), batch_size):
                batch = all_messages[i:i + batch_size]
                tasks = [
                    baixar_arquivo(message, folder_name, global_progress_bar, channel, downloaded_hashes,
                                   file_index + i + j + 1, total_files)
                    for j, message in enumerate(batch)
                ]
                try:
                    await asyncio.gather(*tasks)
                except FloodWaitError:
                    await baixar_todas_midias(client, channel)  # Re-run function

    else:
        print(f"{Fore.RED}Nenhuma mídia encontrada para o tipo selecionado.{Style.RESET_ALL}")
        logger.info(f"Nenhuma mídia encontrada para o tipo selecionado.")
    print(f"{Fore.YELLOW}---------------------------------------------------------------------{Style.RESET_ALL}")


async def main():
    print(f"{Fore.YELLOW}Conectando ao Telegram...{Style.RESET_ALL}")
    logger.info("Conectando ao Telegram...")
    try:
        async with TelegramClient(session_name, api_id, api_hash) as client:
            print(f"{Fore.GREEN}Conectado com sucesso!{Style.RESET_ALL}")
            logger.info("Conectado ao Telegram com sucesso!")

            while True:
                action = input(
                    f"{Fore.CYAN}Digite 'listar' para listar canais/grupos ou 'baixar' para baixar mídias: {Style.RESET_ALL}"
                ).lower()

                if action == "listar":
                    available_channels = await listar_canais_disponiveis(client)
                    if available_channels:
                        channel_choice = input(
                            f"{Fore.CYAN}Digite o número ou o nome/username do canal que você quer baixar: {Style.RESET_ALL}"
                        )
                        try:
                            channel_index = int(channel_choice) - 1
                            if 0 <= channel_index < len(available_channels):
                                channel = available_channels[channel_index]
                            else:
                                raise ValueError("Número inválido")
                        except ValueError:
                            try:
                                channel = next(
                                    entity
                                    for entity in available_channels
                                    if (
                                            hasattr(entity, "title")
                                            and entity.title == channel_choice
                                    )
                                    or (
                                            hasattr(entity, "first_name")
                                            and f"{entity.first_name} {entity.last_name}"
                                            == channel_choice
                                    )
                                    or str(entity.id) == channel_choice
                                )
                            except StopIteration:
                                print(f"{Fore.RED}Canal não encontrado.{Style.RESET_ALL}")
                                logger.error(f"Canal não encontrado: {channel_choice}")
                                continue

                        print(f"{Fore.YELLOW}Canal selecionado: ", end="")
                        if hasattr(channel, "title"):
                            print(
                                f"{channel.title} (ID: {channel.id}){Style.RESET_ALL}"
                            )
                        elif hasattr(channel, "first_name"):
                            print(
                                f"{channel.first_name} {channel.last_name} (ID: {channel.id}){Style.RESET_ALL}"
                            )
                        else:
                            print(f"ID do usuário: {channel.id}{Style.RESET_ALL}")

                        await baixar_todas_midias(client, channel)
                        break
                elif action == "baixar":
                    channel_username = input(
                        f"{Fore.CYAN}Digite o nome ou username do canal: {Style.RESET_ALL}"
                    )
                    try:
                        channel = await client.get_entity(channel_username)
                        print(
                            f"{Fore.YELLOW}Canal encontrado: {channel.title} (ID: {channel.id}){Style.RESET_ALL}"
                        )
                        logger.info(f"Canal encontrado: {channel.title} (ID: {channel.id})")
                    except ValueError:
                        print(f"{Fore.RED}Username do canal inválido. Saindo...{Style.RESET_ALL}")
                        logger.error(f"Username do canal inválido: {channel_username}")
                        continue
                    except Exception as e:
                        print(f"{Fore.RED}Ocorreu um erro: {e}{Style.RESET_ALL}")
                        logger.error(f"Ocorreu um erro: {e}")
                        continue

                    await baixar_todas_midias(client, channel)
                    break
                else:
                    print(
                        f"{Fore.RED}Ops, não identifiquei esse comando. Tente novamente com 'listar' ou 'baixar'.{Style.RESET_ALL}")
                    logger.error(f"Comando inválido digitado: {action}")
                    continue


    except Exception as e:
        print(f"{Fore.RED}Falha ao conectar, ocorreu um erro: {e}{Style.RESET_ALL}")
        logger.error(f"Falha ao conectar: {e}")


if __name__ == "__main__":
    asyncio.run(main())