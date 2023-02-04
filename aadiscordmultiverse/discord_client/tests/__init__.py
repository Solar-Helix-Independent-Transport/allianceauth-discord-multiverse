TEST_GUILD_ID = 123456789012345678
TEST_USER_ID = 198765432012345678
TEST_USER_NAME = 'Peter Parker'
TEST_USER_DISCRIMINATOR = '1234'
TEST_BOT_TOKEN = 'abcdefhijlkmnopqastzvwxyz1234567890ABCDEFGHOJKLMNOPQRSTUVWXY'
TEST_ROLE_ID = 654321012345678912


def create_role(id: int, name: str, managed=False) -> dict:
    return {
        'id': int(id),
        'name': str(name),
        'managed': bool(managed)
    }


def create_matched_role(role, created=False) -> tuple:
    return role, created


ROLE_ALPHA = create_role(1, 'alpha')
ROLE_BRAVO = create_role(2, 'bravo')
ROLE_CHARLIE = create_role(3, 'charlie')
ROLE_CHARLIE_2 = create_role(4, 'Charlie')  # Discord roles are case sensitive
ROLE_MIKE = create_role(13, 'mike', True)


ALL_ROLES = [ROLE_ALPHA, ROLE_BRAVO, ROLE_CHARLIE, ROLE_MIKE]


def create_user_info(
    id: int = TEST_USER_ID,
    username: str = TEST_USER_NAME,
    discriminator: str = TEST_USER_DISCRIMINATOR
):
    return {
        'id': str(id),
        'username': str(username[:32]),
        'discriminator': str(discriminator[:4])
    }
