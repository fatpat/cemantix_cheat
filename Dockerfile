FROM python:3.9-alpine

RUN apk add --no-cache build-base
RUN apk add --no-cache py3-numpy py3-numpy-dev py3-scipy
RUN find /usr/lib/python3.9/site-packages -iname "*.so" -exec sh -c 'x="{}"; mv "$x" "${x/cpython-39-x86_64-linux-musl./}"' \;
ENV PYTHONPATH=/usr/lib/python3.9/site-packages
RUN pip install requests humanize gensim
COPY frWac_postag_no_phrase_700_skip_cut50.bin /
COPY cemantix_cheat.py /
WORKDIR /
ENTRYPOINT ["python3", "cemantix_cheat.py"]
