# Network Security Lab2
This lab is the simulation and implementation of TLS protocol.
## Instructions
An application layer called echotest in Playground project is used for testing. Use
```
python3 ~/Playground3/src/test/echotest.py server -stack=lab2protocol
```
to start the server and 
```
python3 ~/Playground3/src/test/echotest.py [server's playground IP] -stack=lab2protocol
```
to make a connection.

The keys and certificates need to be set up for PLS protocol to correctly work. They can be found under `server_certificate` and `client_certificate`.
```
# Generate Private Key
openssl ecparam -name secp256k1 -genkey -noout -out private_key.pem

# Generate CSR
openssl req -new -key private_key.pem -out req.csr

# Generate Certificate
openssl x509 -CA ca.cert -CAkey private.key -CAcreateserial -in req.csr -req -days 365 -sha256 -out self.cert
```
