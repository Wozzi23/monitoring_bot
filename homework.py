import logging
import os
import sys
import time
from typing import Dict, List, Union

import requests
import telegram

from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN: str = os.getenv('TOKEN_PRACTICUM')
TELEGRAM_TOKEN: str = os.getenv('TOKEN_TELEGRAM')
TELEGRAM_CHAT_ID: str = os.getenv('CHAT_ID')

RETRY_TIME: int = 600
ENDPOINT: str = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS: Dict[str, str] = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES: Dict[str, str] = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='main.log',
    level=logging.DEBUG)


def send_message(bot, message: str) -> None:
    """Отправка сообщения через бота в чат."""
    bot.send_message(TELEGRAM_CHAT_ID, message)
    logging.info(f'Бот отправил сообщение "{message}"')


def get_api_answer(current_timestamp: int) -> (
        Dict[str, List[Union[int, str]]]
):
    """Функция запроса данных с API, возвращает ответ формата JSON."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        raise Exception(f'Эндпоинт {ENDPOINT} не доступен. '
                        f'Код ответа API: {response.status_code}'
                        )
    response = response.json()
    return response


def check_response(response: dict) -> dict:
    """Проверка ответа API на корректность."""
    homeworks = response['homeworks']
    if list(homeworks):
        return homeworks[0]
    else:
        return homeworks


def parse_status(homework) -> str:
    """Функция обрабатывает конкретную домашнюю работу.
    Выдает результат из словаря HOMEWORK_STATUSES.
    """
    if 'homework_name' not in homework:
        raise KeyError('homework_name отсутствует в homework')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Функция проверяет доступность переменных окружения.
    Они необходимы для работы программы.
    """
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    for key, value in tokens.items():
        if value is None:
            logging.critical(
                f'Отсутствует обязательная переменная окружения:{key}'
            )
            return False
    return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit('Программа принудительно остановлена')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            updated_homework = check_response(response)
            try:

                status = parse_status(updated_homework)
                send_message(bot, status)

            except Exception:
                logging.debug('Статус домашней работы не обновлен ревьюеромs')

            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
            time.sleep(RETRY_TIME)
        else:
            ...


if __name__ == '__main__':
    main()
