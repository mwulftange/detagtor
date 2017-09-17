detagtor
===

The *detagtor* detects tagged versions of web applications based on its source code respository. It can be used to detect the installed version of a web application that does not disclose its version itself.

This tool consists of two basic commands:

* *index* builds a knowledge base of fingerprints of the files found in the source code repository at tagged commits.
* *detect* tries to detect the best match of tags found based on the fingerprint of remotely retrieved files from a deployed web application.

Basic usage:

```
user@host:~$ git clone https://github.com/mwulftange/detagtor
user@host:~$ git clone https://github.com/WordPress/WordPress
user@host:~$ cd WordPress
user@host:~/WordPress$ ~/detagtor/detagtor.py index --incude="*.{css,js}" > wordpress.index.json
user@host:~/WordPress$ ~/detagtor/detagtor.py detect -i wordpress.index.json https://www.wordpress.org/
```

