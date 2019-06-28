import unittest
import os
import sys

from mock import patch, call
# Need to append server root path to ensure we can import the necessary files.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decorators import get_menu_entries, get_permissible_entries


class TestGetMenuEntries(unittest.TestCase):

    @patch('mod_auth.models.User')
    @patch('decorators.get_permissible_entries')
    def test_get_menu_entries_with_simple_entries(self, mock_permissible_entries, mock_user):
        """
        Passing a menu entry to get_menu_entries() when all the
        routes are accessible (simulating admin)
        and verifying against correct menu structure by mocking get_permissible_entries()
        and testing that it is called properly
        """

        mu = mock_user.return_value
        mu.can_access_route.return_value = True  # Assuming all routes can be accessed by the user

        def side_effect(*args):
            return args[1]  # Return second argument : entry (dict) assuming user can access all entries

        mock_permissible_entries.side_effect = side_effect
        entries = get_menu_entries(
            mu, 'Configuration', 'cog', '', [
                {'title': 'Notif. services', 'icon': 'bell-o', 'route':
                    'config.notifications', 'entries': [{'title': 'Notif. services', 'icon': 'bell-o', 'route':
                    'config.notifications', 'entries': [{'title': 'Honeypot services', 'icon': 'sliders', 'route':
                    'config.services', 'entries': [{'title': 'Profile mgmt', 'icon': 'bookmark', 'route':
                    'honeypot.profiles'}]}]}]},
                {'title': 'Data processing', 'icon': 'exchange', 'route':
                    'config.data_processing'},
                {'title': 'Honeypot services', 'icon': 'sliders', 'route':
                    'config.services'}
            ]
        )
        correct_entries = {'entries': [{'title': 'Notif. services', 'route': 'config.notifications', 'entries': [
            {'title': 'Notif. services', 'route': 'config.notifications', 'entries': [
                {'title': 'Honeypot services', 'route': 'config.services',
                 'entries': [{'title': 'Profile mgmt', 'route': 'honeypot.profiles', 'icon': 'bookmark'}],
                 'icon': 'sliders'}], 'icon': 'bell-o'}], 'icon': 'bell-o'},
                                       {'route': 'config.data_processing', 'title': 'Data processing',
                                        'icon': 'exchange'},
                                       {'route': 'config.services', 'title': 'Honeypot services', 'icon': 'sliders'}],
                           'icon': 'cog', 'title': 'Configuration'}
        calls = [
            call(mu, {'route': 'config.notifications', 'icon': 'bell-o', 'entries': [
                {'route': 'config.notifications', 'icon': 'bell-o', 'entries': [
                    {'route': 'config.services', 'icon': 'sliders',
                     'entries': [{'route': 'honeypot.profiles', 'icon': 'bookmark', 'title': 'Profile mgmt'}],
                     'title': 'Honeypot services'}], 'title': 'Notif. services'}], 'title': 'Notif. services'}),
            call(mu, {'route': 'config.data_processing', 'icon': 'exchange', 'title': 'Data processing'}),
            call(mu, {'route': 'config.services', 'icon': 'sliders', 'title': 'Honeypot services'})
        ]

        self.assertDictEqual(entries, correct_entries)
        mock_permissible_entries.assert_has_calls(calls)  # Check that mocked function correctly called

    @patch('mod_auth.models.User')
    @patch('decorators.get_permissible_entries')
    def test_get_menu_entries_with_no_permissions(self, mock_permissible_entries, mock_user):
        """
        Passing a menu entry to get_menu_entries() when user is not
        allowed to access any route. This should return an empty dictionary.
        """

        mu = mock_user.return_value
        mu.can_access_route.return_value = False

        def side_effect(*args):
            return args[1]  # Return second argument : entry (dict) assuming user can access all entries

        mock_permissible_entries.side_effect = side_effect
        entries = get_menu_entries(
            mu, 'Configuration', 'cog', '', [
                {'title': 'Notif. services', 'icon': 'bell-o', 'route':
                    'config.notifications', 'entries': [{'title': 'Notif. services', 'icon': 'bell-o', 'route':
                    'config.notifications', 'entries': [{'title': 'Honeypot services', 'icon': 'sliders', 'route':
                    'config.services', 'entries': [{'title': 'Profile mgmt', 'icon': 'bookmark', 'route':
                    'honeypot.profiles'}]}]}]},
                {'title': 'Data processing', 'icon': 'exchange', 'route':
                    'config.data_processing'},
                {'title': 'Honeypot services', 'icon': 'sliders', 'route':
                    'config.services'}
            ]
        )
        correct_entries = {}
        self.assertDictEqual(entries, correct_entries)
        mock_permissible_entries.assert_not_called()


class TestGetPermissibleEntries(unittest.TestCase):

    @patch('mod_auth.models.User')
    def test_get_permissible_entries_with_simple_menu(self, mock_user):
        """
        Passing a menu entry to get_permissible_entries() when all the
        routes are accessible (simulating admin)
        and verifying against correct menu structure.
        """

        mu = mock_user.return_value
        mu.can_access_route.return_value = True

        entries = get_permissible_entries(mu, {'title': 'Notif. services', 'icon': 'bell-o', 'route':
            'config.notifications', 'entries': [{'title': 'Notif. services', 'icon': 'bell-o', 'route':
            'config.notifications', 'entries': [{'title': 'Honeypot services', 'icon': 'sliders', 'route':
            'config.services', 'entries': [{'title': 'Profile mgmt', 'icon': 'bookmark', 'route':
            'honeypot.profiles'}]}]}]})
        correct_entries = {'title': 'Notif. services', 'route': 'config.notifications', 'entries': [
            {'title': 'Notif. services', 'route': 'config.notifications', 'entries': [
                {'title': 'Honeypot services', 'route': 'config.services',
                 'entries': [{'title': 'Profile mgmt', 'route': 'honeypot.profiles', 'icon': 'bookmark'}],
                 'icon': 'sliders'}], 'icon': 'bell-o'}], 'icon': 'bell-o'}

        self.assertDictEqual(entries, correct_entries)

    @patch('mod_auth.models.User')
    def test_get_permissible_entries_with_no_permissions(self, mock_user):
        """
        Passing a menu entry to get_permissible_entries() when the user is not
        allowed to access any route in the passed entries. This should return an empty dictionary.
        """

        mu = mock_user.return_value
        mu.can_access_route.return_value = False
        entries = get_permissible_entries(mu, {'title': 'Notif. services', 'icon': 'bell-o', 'route':
            'config.notifications', 'entries': [{'title': 'Notif. services', 'icon': 'bell-o', 'route':
            'config.notifications', 'entries': [{'title': 'Honeypot services', 'icon': 'sliders', 'route':
            'config.services', 'entries': [{'title': 'Profile mgmt', 'icon': 'bookmark', 'route':
            'honeypot.profiles'}]}]}]})
        correct_entries = {}
        self.assertDictEqual(entries, correct_entries)

    @patch('mod_auth.models.User')
    def test_get_permissible_entries_with_partial_permissions(self, mock_user):
        """
        Passing a menu entry to the function get_permissible_entries() when the user is not
        allowed to access the route of one of the sub-entries
        having 'route' as 'honeypot.profiles'
        This should return a dictionary without this particular entry.
        """
        mu = mock_user.return_value

        def side_effect(*args):
            return args[0] != 'honeypot.profiles'

        mu.can_access_route.side_effect = side_effect
        entries = get_permissible_entries(mu, {'title': 'Notif. services', 'icon': 'bell-o', 'route':
            'config.notifications', 'entries': [{'title': 'Notif. services', 'icon': 'bell-o', 'route':
            'config.notifications', 'entries': [{'title': 'Honeypot services', 'icon': 'sliders', 'route':
            'config.services', 'entries': [{'title': 'Profile mgmt', 'icon': 'bookmark', 'route':
            'honeypot.profiles'}]}]}]})
        correct_entries = {'title': 'Notif. services', 'route': 'config.notifications', 'entries': [
            {'title': 'Notif. services', 'route': 'config.notifications',
             'entries': [{'title': 'Honeypot services', 'route': 'config.services', 'icon': 'sliders'}],
             'icon': 'bell-o'}], 'icon': 'bell-o'}
        self.assertDictEqual(entries, correct_entries)


if __name__ == "__main__":
    unittest.main()
