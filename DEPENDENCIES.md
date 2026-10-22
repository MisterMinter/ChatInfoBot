Python dependencies are maintained in `requirements.in`. The generated `requirements.txt` pins every dependency and its package hashes. Install with:

```sh
python -m pip install --require-hashes -r requirements.txt
```

To update, use Python 3.12 and pip-tools, then review and audit the regenerated lock:

```sh
pip-compile --upgrade --generate-hashes --no-emit-index-url --no-emit-trusted-host --output-file=requirements.txt requirements.in
pip-audit -r requirements.txt --disable-pip --no-deps
```
