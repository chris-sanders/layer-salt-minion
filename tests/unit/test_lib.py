#!/usr/bin/python3


class TestLib():
    def test_pytest(self):
        assert True

    def test_saltminion(self, saltminion):
        ''' See if the helper fixture works to load charm configs '''
        assert isinstance(saltminion.charm_config, dict)

    # Include tests for functions in lib_salt_minion
