detagtor
===

The *detagtor* detects tagged versions of web applications based on its source code respository. It can be used to detect the installed version of a web application that does not disclose its version itself.

This tool consists of two basic commands:

* *index* builds a knowledge base of fingerprints of the files found in the source code repository at tagged commits.
* *detect* tries to detect the best match of tags found based on the fingerprint of remotely retrieved files from a deployed web application.

Basic usage:

```
ubuntu@ubuntu:~$ git clone https://github.com/mwulftange/detagtor
ubuntu@ubuntu:~$ git clone https://github.com/WordPress/WordPress
ubuntu@ubuntu:~$ cd WordPress
ubuntu@ubuntu:~/WordPress$ ~/detagtor/detagtor.py index --include "*.{css,js,txt}" -v > wordpress.index.json
ubuntu@ubuntu:~/WordPress$ ~/detagtor/detagtor.py detect https://www.wordpress.com/ -v < wordpress.index.json
```

[![asciicast](https://asciinema.org/a/VwSMZa9UATh9r6RrfwQr3MeZT.png)](https://asciinema.org/a/VwSMZa9UATh9r6RrfwQr3MeZT)

