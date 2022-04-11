"""Telegram-бот обращается к API Практикум.Домашка и узнает статус ДР."""
import os
import time
import requests
import telegram
import logging

import exceptions
from http import HTTPStatus
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    format=(
        '%(asctime)s, %(levelname)s, %(name)s, %(funcName)s:%(lineno)d, '
        '%(message)s'
    )
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(name)s, %(funcName)s:%(lineno)d, '
    '%(message)s'
)
handler.setFormatter(formatter)
# logger.info('test INFO-level log record')


def send_message(bot, message):
    """Отправка сообщение в Telegram-чат, определяемый переменной окружения."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info(f'Бот отправил сообщение: {message}')

    except exceptions.SendMessageError:
        logger.error('Ошибка: бот не смог отправить сообщение')


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        # response = requests.get(ENDPOINT, HEADERS, params=params)

    except exceptions.APIStatusCodeException:
        logger.error(f'Ошибка обращения к эндпоинту {ENDPOINT}')

    if response.status_code != HTTPStatus.OK:
        error_message = (
            f'Ошибка обращения к эндпоинту {ENDPOINT}, '
            f'код ответа API: {response.status_code}'
        )
        logger.error(error_message)
        raise exceptions.APIStatusCodeException(error_message)

    return response.json()


def check_response(response):
    """Поверяет ответ API на корректность."""
    try:
        homeworks_list = response['homeworks']

    except KeyError as error:
        error_message = f'Ошибка доступа по ключу homeworks: {error}'
        logger.error(error_message)
        raise exceptions.CheckResponseException(error_message)

    if homeworks_list is None:
        error_message = 'В ответе API нет списка домашних работ'
        logger.error(error_message)
        raise exceptions.CheckResponseException(error_message)

    if len(homeworks_list) == 0:
        error_message = 'За последнее время домашних работ не найдено'
        logger.error(error_message)
        raise exceptions.CheckResponseException(error_message)

    if not isinstance(homeworks_list, list):
        error_message = 'В ответе API домашние работы представлены не списком'
        logger.error(error_message)
        raise exceptions.CheckResponseException(error_message)

    return homeworks_list


def parse_status(homework):
    """Извлекает из информации о домашней работе статус этой работы."""
    try:
        homework_name = homework.get('homework_name')

    except KeyError as error:
        error_message = f'Ошибка доступа по ключу homework_name: {error}'
        logger.error(error_message)

    try:
        homework_status = homework.get('status')

    except KeyError as error:
        error_message = f'Ошибка доступа по ключу status: {error}'
        logger.error(error_message)

    verdict = HOMEWORK_STATUSES[homework_status]

    if verdict is None:
        error_message = 'Неизвестный статус домашней работы'
        logger.error(error_message)
        raise exceptions.StatusIsUnknownException(error_message)

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения, необходимых для работы."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        error_message = 'Отсутствует необходимый токен'
        logger.critical(error_message)
        raise exceptions.RequiredTokenIsMissingException(error_message)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    # точка отсчета, временная метка - unix-time в сек. 1мес. назад - 2629743
    # 10 минут назад - 600
    current_timestamp = int(time.time() - 600)
    earlier_error = None
    earlier_status = None

    while True:
        try:
            response = get_api_answer(current_timestamp)

        except exceptions.APIResponseIsIncorrectException as error:
            if str(error) != earlier_error:
                earlier_error = str(error)
                send_message(bot, error)
            logger.error(error)
            time.sleep(RETRY_TIME)
            continue

        try:
            homeworks = check_response(response)
            homeworks_status = homeworks[0].get('status')
            if homeworks_status != earlier_status:
                earlier_status = homeworks_status
                message = parse_status(homeworks[0])
                send_message(bot, message)
            else:
                logger.debug('Обновления статуса отсутствуют')

            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            print(message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
