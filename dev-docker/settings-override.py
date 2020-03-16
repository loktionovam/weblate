print("Start 'settings-override.py'")

if "WEBLATE_AUTH_LDAP_SERVER_URI" in os.environ:
    print("Start defining custom active directory authentication")
    import ldap
    from django_auth_ldap.config import LDAPSearch
    AUTH_LDAP_USER_DN_TEMPLATE = None
    AUTH_LDAP_VALIDATE_TLS = get_env_bool("WEBLATE_AUTH_LDAP_VALIDATE_TLS", True)

    if not AUTH_LDAP_VALIDATE_TLS:
        AUTH_LDAP_GLOBAL_OPTIONS = {
            ldap.OPT_X_TLS_REQUIRE_CERT: ldap.OPT_X_TLS_NEVER
        }

    AUTH_LDAP_USER_SEARCH_BASE = os.environ.get("WEBLATE_AUTH_LDAP_USER_SEARCH_BASE", "dc=example,dc=com")
    AUTH_LDAP_USER_SEARCH_FILTER = os.environ.get("WEBLATE_AUTH_LDAP_USER_SEARCH_FILTER", "(sAMAccountName=%(user)s)")
    AUTH_LDAP_USER_SEARCH = LDAPSearch(AUTH_LDAP_USER_SEARCH_BASE, ldap.SCOPE_SUBTREE, AUTH_LDAP_USER_SEARCH_FILTER)

    if DEBUG:
        print("'AUTH_LDAP_USER_DN_TEMPLATE': '%s'" % AUTH_LDAP_USER_DN_TEMPLATE)
        print("'AUTH_LDAP_VALIDATE_TLS': '%s'" % AUTH_LDAP_VALIDATE_TLS)
        print("'AUTH_LDAP_USER_SEARCH_BASE: '%s'" % AUTH_LDAP_USER_SEARCH_BASE)
        print("'AUTH_LDAP_USER_SEARCH_FILTER': '%s'" % AUTH_LDAP_USER_SEARCH_FILTER)

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly"
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
        "weblate.api.authentication.BearerAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {"anon": "100/day"},
    "DEFAULT_PAGINATION_CLASS": ("rest_framework.pagination.PageNumberPagination"),
    "PAGE_SIZE": 20,
    "VIEW_DESCRIPTION_FUNCTION": "weblate.api.views.get_view_description",
    "UNAUTHENTICATED_USER": "weblate.auth.models.get_anonymous",
}


DEFAULT_PUSH_ON_COMMIT = False

DEFAULT_COMMIT_MESSAGE = (
    '[{{ component_name }}] Translated using Weblate ({{ language_name }})\n\n'
    'Currently translated at {{ stats.translated_percent }}% '
    '({{ stats.translated }} of {{ stats.all }} strings)\n\n'
    'Translation: {{ project_name }}/{{ component_name }}\n'
    'Translate-URL: {{ url }}'
)

DEFAULT_ADD_MESSAGE = '[{{ component_name }}] Added translation using Weblate ({{ language_name }})\n\n'

DEFAULT_DELETE_MESSAGE = (
    '[{{ component_name }}] Deleted translation using Weblate ({{ language_name }})\n\n'
)

DEFAULT_MERGE_MESSAGE = (
    "[{{ component_name }}] Merge branch '{{ component_remote_branch }}' into Weblate.\n\n"
)

DEFAULT_ADDON_MESSAGE = '''[{{ component_name }}] Update translation files

Updated by "{{ addon_name }}" hook in Weblate.

Translation: {{ project_name }}/{{ component_name }}
Translate-URL: {{ url }}'''

DEFAULT_PULL_MESSAGE = '''[{{ component_name }}] Translations update from Weblate

Translations update from [Weblate]({{url}}) for {{ project_name }}/{{ component_name }}.
'''
