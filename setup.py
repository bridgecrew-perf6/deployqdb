from setuptools import setup

setup(name='deployqdb',
      version='0.1',
      description='Simple web service to deploy Quest instances on k8s',
      url='http://github.com/picoDoc/deployqdb',
      author='Matt Doherty',
      author_email='matt.d.doc@gmail.com',
      license='MIT',
      packages=['deployqdb'],
      install_requires=[
          'pytest',
          'uvicorn',
          'fastapi',
          'kubernetes'
      ],
      zip_safe=False)
