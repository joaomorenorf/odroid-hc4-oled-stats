from setuptools import setup

setup(
        name = 'odroid-homecloud',
        version = '0.4.1',
        description = 'System statistics for the ODROID HC4 OLED display',
        author = 'Dongjin Kim',
        author_email = 'tobetter@gmail.com',
        license = 'MIT',
        install_requires = [
            'luma.core >= 1.17.1',
            'luma.oled >= 3.6.0',
            ],
        packages = [
            'odroid_homecloud_display'
            ],
        entry_points = {
            'console_scripts' : [
                'odroid_homecloud_display = odroid_homecloud_display.clock:main']
            },
        zip_safe = False)
