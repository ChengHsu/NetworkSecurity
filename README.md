# JHU - Network Security Fall 2018
The project mainly contains documents and codes of two labs from network security class. The objective of this project is to design a "middleware" network over the simulated wire protocol defined by the [Playground project](https://github.com/CrimsonVista/Playground3) from Dr.Seth Neilson.

The "middleware" network designs and implements two protocols which take inspiration from TCP and TLS 1.3 to provide reliable and secure data transmission separately.
## Lab1
Lab1(RIPP protocol) is the simulation and implementation of TCP protocol. It provides relaible and error free data transmissions.
- The Playground RFC for the Reliable Internetwork Playground Protocol (RIPP) can be found under `docs/prfc/drafts/reliable.{txt,xml}`
- The source code for RTPP protocol can be found under `lab1protocol`
## Lab2
Lab2(SITH protocol) is the simulation and implementation of TLS protocol. It provides confidentiality, message integrity, and mutual authentication over the reliable transport layer RIPP.
- The Playground RFC for the Secure Internetwork Transport Handshake (SITH) can be found under `docs/prfc/drafts/secure.{txt,xml}`
- The source code for SITH protocol can be found under `lab2protocol`
