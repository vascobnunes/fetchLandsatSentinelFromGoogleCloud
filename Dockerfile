FROM petkr/gdal-python-alpine
RUN apk update
RUN apk add git
RUN apk add g++
RUN git clone https://github.com/vascobnunes/fetchLandsatSentinelFromGoogleCloud
RUN pip install --upgrade pip
RUN pip install numpy
RUN pip install fels
ENTRYPOINT ["fels"]
CMD []