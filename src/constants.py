from pathlib import Path

MESSAGE_STRING = ('PEP Url: {}\n'
                  'Статус в карточке: {}\n'
                  'Ожидаемые статусы: {}\n\n')

EXPECTED_STATUS = {
    'A': ('Active', 'Accepted'),
    'D': ('Deferred',),
    'F': ('Final',),
    'P': ('Provisional',),
    'R': ('Rejected',),
    'S': ('Superseded',),
    'W': ('Withdrawn',),
    '': ('Draft', 'Active'),
}
MAIN_PEP_URL = 'https://peps.python.org/'
MAIN_DOC_URL = 'https://docs.python.org/3/'
BASE_DIR = Path(__file__).parent
DATETIME_FORMAT = '%Y-%m-%d_%H-%M-%S'
LOG_FORMAT = '%(asctime)s - [%(levelname)s] - %(message)s'
DT_FORMAT = '%d.%m.%Y %H:%M:%S'
