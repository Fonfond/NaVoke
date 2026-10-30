import yaml
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def load_compose():
    return yaml.safe_load((ROOT / 'docker-compose.yml').read_text(encoding='utf-8'))


def test_no_hardcoded_database_password():
    compose_text = (ROOT / 'docker-compose.yml').read_text(encoding='utf-8')
    settings_text = (ROOT / 'navoke_backend/settings.py').read_text(encoding='utf-8')
    assert '492357816' not in compose_text
    assert '492357816' not in settings_text


def test_database_and_redis_ports_are_not_published():
    compose = load_compose()
    assert 'ports' not in compose['services']['db']
    assert 'ports' not in compose['services']['redis']
    assert compose['services']['web']['ports'] == ['8000:8000']


def test_postgres_password_is_fail_closed_variable():
    db_env = load_compose()['services']['db']['environment']
    assert db_env['POSTGRES_PASSWORD'].startswith('${POSTGRES_PASSWORD')
    assert '492357816' not in db_env['POSTGRES_PASSWORD']


def test_redis_requires_password():
    redis = load_compose()['services']['redis']
    assert 'REDIS_PASSWORD' in redis['environment']
    assert '--requirepass' in redis['command']
    assert 'REDIS_PASSWORD' in ' '.join(redis['command'])


def test_web_uses_env_secrets_and_database_url():
    web_env = load_compose()['services']['web']['environment']
    joined = '\n'.join(web_env)

    assert 'DATABASE_URL=${DATABASE_URL' in joined
    assert 'REDIS_PASSWORD' in joined
    assert 'FIREBASE_CREDENTIALS' in joined
    assert 'YOOKASSA_SECRET_KEY' in joined
    assert 'DB_PASSWORD' not in joined


def test_env_example_lists_all_required_variables():
    env_example = (ROOT / '.env.example').read_text(encoding='utf-8')
    required = (
        'DJANGO_SECRET_KEY',
        'POSTGRES_PASSWORD',
        'DATABASE_URL',
        'REDIS_PASSWORD',
        'YOOKASSA_SHOP_ID',
        'YOOKASSA_SECRET_KEY',
        'FIREBASE_CREDENTIALS',
    )
    for key in required:
        assert key in env_example
    assert '492357816' not in env_example
