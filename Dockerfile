FROM python:latest

RUN apt-get update
#NMAP & dnsrecon
RUN apt-get install -y nmap dnsrecon python-dev-is-python3
RUN pip3 install pipx
RUN pipx install cython
RUN pipx ensurepath

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


# Smbmap as smbmap
RUN git clone https://github.com/ShawnDEvans/smbmap /home/smbmap/ && \
	sed -i 's/pycrypto/pycryptodome/gm' /home/smbmap/setup.py && \
	pipx install /home/smbmap/
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
RUN git clone https://gitlab.com/exploit-database/exploitdb /opt/exploitdb
RUN sed 's|path_array+=(.*)|path_array+=("/opt/exploitdb")|g' /opt/exploitdb/.searchsploit_rc > ~/.searchsploit_rc
RUN ln -sf /opt/exploitdb/searchsploit /usr/local/bin/searchsploit

#CRTSH
RUN git clone https://github.com/YashGoti/crtsh.py.git /home/crtsh && cd /home/crtsh && pip3 install argparse feedparser && mv crtsh.py crtsh && chmod +x crtsh && ln -s /home/crtsh/crtsh /usr/bin/crtsh
# Dirsearch as dirsearch.py
RUN python3 -m pipx install dirsearch
#CME
# RUN git clone --recursive https://github.com/byt3bl33d3r/CrackMapExec /home/cme/
# WORKDIR /home/cme/
# RUN pip install --upgrade pynacl
# RUN pip install --upgrade cryptography
# RUN pip install --upgrade pycrypto
# RUN pip install --upgrade pycryptodome
# RUN pip install --upgrade asn1crypto
# RUN mkdir /home/cme && wget https://github.com/Porchetta-Industries/CrackMapExec/releases/download/v5.3.0/cme-ubuntu-latest-3.10.zip -O /home/cme/cme.zip && unzip /home/cme/cme.zip -d /home/cme 
# RUN cd /home/cme && chmod u+x /home/cme/cme && ln -s /home/cme/cme /usr/bin/cme && cme smb
RUN python3 -m pipx install crackmapexec

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
RUN wget -c https://go.dev/dl/go1.20.8.linux-amd64.tar.gz -O - | tar xzv -C /usr/local/
ENV PATH=$PATH:/usr/local/go/bin:/root/go/bin/
#RUN git clone https://github.com/projectdiscovery/nuclei.git /home/nuclei && cd /home/nuclei/v2/cmd/nuclei && go build && mv nuclei /usr/local/bin/ && nuclei -ut
RUN go install -v github.com/projectdiscovery/nuclei/v2/cmd/nuclei@latest

#NIKTO
RUN git clone https://github.com/sullo/nikto /home/nikto && cd /home/nikto/program && git checkout nikto-2.5.0 && chmod u+x ./nikto.pl && \
	ln -s /home/nikto/program/nikto.pl /usr/bin/nikto


# Pollenisator
WORKDIR /home/Pollenisator
# Set timezone
RUN apt-get install -y tzdata
ENV TZ Europe/Paris
#RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN git clone https://github.com/fbarre96/PollenisatorGUI /home/Pollenisator/PollenisatorGUI
RUN pipx install /home/Pollenisator/PollenisatorGUI
# init cme db first run
RUN /root/.local/bin/cme -h
# RUn pollworker
WORKDIR /home/Pollenisator
RUN mkdir -p /root/.config/pollenisator-gui/
COPY config/client.cfg /root/.config/pollenisator-gui/
CMD ["/root/.local/pipx/venvs/pollenisator-gui/bin/pollworker"]