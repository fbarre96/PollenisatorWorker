FROM python:latest

RUN apt-get update
#NMAP & dnsrecon
RUN apt-get install -y nmap dnsrecon 
# Test SSL as testssl
RUN apt-get install -y bsdmainutils dnsutils
RUN git clone --depth 1 https://github.com/drwetter/testssl.sh.git /home/testssl.sh && \
	chmod +x /home/testssl.sh/testssl.sh && \
	ln -s /home/testssl.sh/testssl.sh /usr/bin/testssl

# Sublist3r as sublist3r
RUN git clone https://github.com/aboul3la/Sublist3r.git /home/sublist3r/ && \
	pip install -r /home/sublist3r/requirements.txt && \
	chmod +x /home/sublist3r/sublist3r.py && \
	ln -s /home/sublist3r/sublist3r.py /usr/bin/sublist3r
# SSH scan as ssh_scan
RUN apt-get install -y ruby-dev rubygems 
RUN gem install ssh_scan


# crtsh as crtsh.py
COPY tools/crtsh /home/crtsh
RUN pip install feedparser && \
	chmod +x /home/crtsh/crtsh.py && \
	ln -s /home/crtsh/crtsh.py /usr/bin/crtsh

# amap as amap
RUN git clone https://github.com/BlackArch/amap/ /home/amap/
WORKDIR /home/amap
RUN ./configure && make && make install


# Smbmap as smbmap.py
RUN git clone https://github.com/ShawnDEvans/smbmap /home/smbmap && \
	pip install -r /home/smbmap/requirements.txt && \
	chmod +x /home/smbmap/smbmap.py && \
	ln -s /home/smbmap/smbmap.py /usr/bin/smbmap.py
# enum4linux as enum4linux.pl
RUN apt-get install -y smbclient
RUN git clone https://github.com/portcullislabs/enum4linux /home/enum4linux && \
	chmod +x /home/enum4linux/enum4linux.pl && \
	ln -s /home/enum4linux/enum4linux.pl /usr/bin/enum4linux.pl
# ikescan as 
RUN git clone https://github.com/royhills/ike-scan /home/ike-scan
WORKDIR /home/ike-scan
RUN autoreconf --install && ./configure --with-openssl && make && make check && make install

# WhatWeb
RUN apt-get install -y whatweb
# bluekeep scanner
RUN git clone https://github.com/robertdavidgraham/rdpscan /home/rdpscan && cd /home/rdpscan && make && ln -s /home/rdpscan/rdpscan /usr/bin/rdpscan
# EternalBlue
RUN wget https://svn.nmap.org/nmap/scripts/smb-vuln-ms17-010.nse -O /usr/share/nmap/scripts/smb-vuln-ms17-010.nse
#Searchsploit
RUN git clone https://github.com/offensive-security/exploitdb.git /opt/exploitdb
RUN sed 's|path_array+=(.*)|path_array+=("/opt/exploitdb")|g' /opt/exploitdb/.searchsploit_rc > ~/.searchsploit_rc
RUN ln -sf /opt/exploitdb/searchsploit /usr/local/bin/searchsploit
#OPenrelay
COPY tools/smtp-open-relay.nse /usr/share/nmap/scripts/smtp-open-relay.nse

# Dirsearch as dirsearch.py
RUN git clone https://github.com/maurosoria/dirsearch.git /home/dirsearch/ && \
	chmod +x /home/dirsearch/dirsearch.py && \
	python -m pip install -r /home/dirsearch/requirements.txt && \
	ln -s /home/dirsearch/dirsearch.py /usr/bin/dirsearch
#CME
# RUN git clone --recursive https://github.com/byt3bl33d3r/CrackMapExec /home/cme/
# WORKDIR /home/cme/
RUN pip install --upgrade pynacl
RUN pip install --upgrade cryptography
RUN pip install --upgrade pycrypto
RUN pip install --upgrade pycryptodome
RUN pip install --upgrade asn1crypto
RUN mkdir /home/cme && wget https://github.com/Porchetta-Industries/CrackMapExec/releases/download/v5.3.0/cme-ubuntu-latest-3.10.zip -O /home/cme/cme.zip && unzip /home/cme/cme.zip -d /home/cme 
RUN cd /home/cme && chmod u+x /home/cme/cme && ln -s /home/cme/cme /usr/bin/cme && cme smb

# Knockpy as knockpy.py
#RUN apt-get install -y python-dnspython
#RUN python3.7 -m pip install setuptools
RUN git clone https://github.com/guelfoweb/knock.git /home/knock && \
	cd /home/knock && \
	chmod +x /home/knock/knockpy/knockpy.py && \
	#python3.7 /home/knock/setup.py install && \
	python /home/knock/setup.py install && \
	ln -s /home/knock/knockpy/knockpy.py /usr/bin/knockpy.py

# Nuclei
RUN wget -c https://go.dev/dl/go1.19.2.linux-amd64.tar.gz -O - | tar xzv -C /usr/local/
ENV PATH=$PATH:/usr/local/go/bin
RUN git clone https://github.com/projectdiscovery/nuclei.git /home/nuclei && cd /home/nuclei/v2/cmd/nuclei && go build && mv nuclei /usr/local/bin/ && nuclei -ut

#NIKTO
RUN git clone https://github.com/sullo/nikto /home/nikto && cd /home/nikto/program && git checkout nikto-2.5.0 && chmod u+x ./nikto.pl && \
	ln -s /home/nikto/program/nikto.pl /usr/bin/nikto


# Pollenisator
WORKDIR /home/Pollenisator
COPY requirements.txt /tmp
# Set timezone
RUN apt-get install -y tzdata
ENV TZ Europe/Paris
#RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN python3 -m pip install -r /tmp/requirements.txt
WORKDIR /home/Pollenisator
CMD ["/bin/bash", "-c", "/home/Pollenisator/startWorker.sh"]
