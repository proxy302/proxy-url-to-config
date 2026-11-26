# proxy-url-to-config: one proxy, ready-to-paste settings for curl, env vars, git, npm, pip and Docker

Write the proxy once as a URL, `http://USER:PASS@HOST:PORT`, with the username and password percent-encoded. Then put that same URL where each tool looks for it. curl takes it with `-x` or in `~/.curlrc`. The shell needs `http_proxy` and `https_proxy` in both spellings, and `HTTPS_PROXY` also starts with `http://`. git uses `http.proxy` (there is no `https.proxy`), npm uses `proxy` and `https-proxy`, and pip uses `global.proxy`. Docker reads `daemon.json` for image pulls and `~/.docker/config.json` for containers and builds, and a systemd drop-in needs every `%` doubled. `proxy2config.py` prints all of these from one input such as `host:port:user:pass`, does the escaping for each format, and can write each one to its own file. Proxy302 maintains this tool and sells proxies. A static residential (ISP) IP costs $7.99 for 30 days, or $0.50 for a one-day test ([prices](https://proxy302.com/pricing/)). The script works with any provider's proxy and never connects anywhere.

> Maintained by [Proxy302](https://proxy302.com). MIT licensed.

## Usage

```bash
git clone https://github.com/proxy302/proxy-url-to-config
cd proxy-url-to-config
python3 proxy2config.py 'HOST:PORT:USER:PASS'                       # the form most providers hand out
python3 proxy2config.py 'http://USER:PASS@HOST:PORT' --only git,npm
python3 proxy2config.py 'socks5h://USER:PASS@HOST:PORT'
python3 proxy2config.py 'HOST:PORT:USER:PASS' --no-proxy 'localhost,127.0.0.1,.corp.example' --write ./proxy-config
```

Python 3.8 or later, standard library only.

- **Input.** `host:port:user:pass` (the password may contain `:` and `@`), `user:pass@host:port`, `host:port`, or a URL. In URL form the password must already be percent-encoded; if it contains `#`, `/` or `?`, use the four-part form and let the script encode it. `--scheme socks5h` sets the protocol for input without one.
- **Output.** Sections `curl`, `env` (bash/zsh and PowerShell), `git`, `npm`, `pip`, `docker`; pick some with `--only`. `--no-proxy` sets the bypass list (default `localhost,127.0.0.1,::1`).
- **`--write DIR`** saves `curlrc`, `proxy-env.sh`, `proxy-env.ps1`, `git-proxy.sh`, `npmrc`, `pip.conf`, `docker-daemon.json`, `docker-http-proxy.conf` and `docker-config.json`, readable only by you, because they contain the password.

## Example output

A password with five awkward characters, `p@ss#w0rd:%/1`:

```text
$ python3 proxy2config.py '127.0.0.1:26128:team-a:p@ss#w0rd:%/1' --write ./out
proxy     http://team-a:****@127.0.0.1:26128
username  'team-a', password 13 characters, both percent-encoded below
no_proxy  localhost,127.0.0.1,::1

== curl

One request:
    curl -x http://team-a:p%40ss%23w0rd%3A%25%2F1@127.0.0.1:26128 https://api.ipify.org

~/.curlrc (or any file passed with curl -K FILE):
    proxy = "http://team-a:p%40ss%23w0rd%3A%25%2F1@127.0.0.1:26128"
    noproxy = "localhost,127.0.0.1,::1"

== Environment variables

bash / zsh (paste into the shell, or into ~/.bashrc or ~/.zshrc):
    export http_proxy=http://team-a:p%40ss%23w0rd%3A%25%2F1@127.0.0.1:26128
    export https_proxy="$http_proxy"
    export HTTP_PROXY="$http_proxy" HTTPS_PROXY="$http_proxy"
    export no_proxy=localhost,127.0.0.1,::1
    export NO_PROXY="$no_proxy"

PowerShell (this window only):
    $env:HTTP_PROXY = 'http://team-a:p%40ss%23w0rd%3A%25%2F1@127.0.0.1:26128'
    $env:HTTPS_PROXY = 'http://team-a:p%40ss%23w0rd%3A%25%2F1@127.0.0.1:26128'
    $env:NO_PROXY = 'localhost,127.0.0.1,::1'

# Both spellings on purpose: curl reads only lower-case http_proxy, other tools read upper case. HTTPS_PROXY also starts with http:// because it names the proxy, not the site.

== git

All https:// remotes:
    git config --global http.proxy http://team-a:p%40ss%23w0rd%3A%25%2F1@127.0.0.1:26128

Only one host:
    git config --global http.https://github.com.proxy http://team-a:p%40ss%23w0rd%3A%25%2F1@127.0.0.1:26128

# There is no https.proxy key in git: http.proxy covers https:// remotes too. Remotes written as git@host:repo use SSH and ignore it. Undo with: git config --global --unset http.proxy

== npm

Commands:
    npm config set proxy http://team-a:p%40ss%23w0rd%3A%25%2F1@127.0.0.1:26128
    npm config set https-proxy http://team-a:p%40ss%23w0rd%3A%25%2F1@127.0.0.1:26128
    npm config set noproxy localhost,127.0.0.1,::1

or these lines in ~/.npmrc:
    proxy=http://team-a:p%40ss%23w0rd%3A%25%2F1@127.0.0.1:26128
    https-proxy=http://team-a:p%40ss%23w0rd%3A%25%2F1@127.0.0.1:26128
    noproxy=localhost,127.0.0.1,::1

== pip

Command:
    pip config set global.proxy http://team-a:p%40ss%23w0rd%3A%25%2F1@127.0.0.1:26128

or pip.conf (Linux ~/.config/pip/pip.conf, macOS ~/Library/Application Support/pip/pip.conf, Windows %APPDATA%\pip\pip.ini):
    [global]
    proxy = http://team-a:p%40ss%23w0rd%3A%25%2F1@127.0.0.1:26128

One install only:
    pip install --proxy http://team-a:p%40ss%23w0rd%3A%25%2F1@127.0.0.1:26128 PACKAGE

== Docker

Image pulls: /etc/docker/daemon.json, then restart Docker (merge into an existing file):
    {
      "proxies": {
        "http-proxy": "http://team-a:p%40ss%23w0rd%3A%25%2F1@127.0.0.1:26128",
        "https-proxy": "http://team-a:p%40ss%23w0rd%3A%25%2F1@127.0.0.1:26128",
        "no-proxy": "localhost,127.0.0.1,::1"
      }
    }

or a systemd drop-in: /etc/systemd/system/docker.service.d/http-proxy.conf (then: sudo systemctl daemon-reload && sudo systemctl restart docker):
    [Service]
    Environment="HTTP_PROXY=http://team-a:p%%40ss%%23w0rd%%3A%%25%%2F1@127.0.0.1:26128"
    Environment="HTTPS_PROXY=http://team-a:p%%40ss%%23w0rd%%3A%%25%%2F1@127.0.0.1:26128"
    Environment="NO_PROXY=localhost,127.0.0.1,::1"

Containers and docker build: ~/.docker/config.json (merge into an existing file):
    {
      "proxies": {
        "default": {
          "httpProxy": "http://team-a:p%40ss%23w0rd%3A%25%2F1@127.0.0.1:26128",
          "httpsProxy": "http://team-a:p%40ss%23w0rd%3A%25%2F1@127.0.0.1:26128",
          "noProxy": "localhost,127.0.0.1,::1"
        }
      }
    }

# In the systemd file every % is doubled, because systemd reads % as a specifier. Values in ~/.docker/config.json become environment variables inside your containers, where anyone who can inspect the container can read the password. Docker Desktop has its own setting: Settings > Resources > Proxies.

wrote curlrc, proxy-env.sh, proxy-env.ps1, git-proxy.sh, npmrc, pip.conf, docker-daemon.json, docker-http-proxy.conf, docker-config.json to ./out (mode 600, they contain the password)
```

## Tested: does each tool get the password right?

Every generated file was used once, through [mock-proxy-server](https://github.com/proxy302/mock-proxy-server) running on 127.0.0.1:26128 and demanding user `team-a` with the password `p@ss#w0rd:%/1`. The target `demo.test:26082` exists only inside the proxy (`--map demo.test=127.0.0.1`), so a request that skipped the proxy could not have reached it. It served a text file, a git repository over HTTP, an npm package record and a pip index page. Recorded on 26 November 2026 on macOS with curl 8.7.1, git 2.54, npm 11.9 and pip 21.2:

```text
$ curl -sS -K out/curlrc http://demo.test:26082/hello.txt
hello through the proxy
$ (. out/proxy-env.sh; curl -sS http://demo.test:26082/hello.txt)
hello through the proxy
$ (. out/proxy-env.sh; python3 -c "import urllib.request as u; print(u.urlopen('http://demo.test:26082/hello.txt').read())")
b'hello through the proxy\n'
$ export GIT_CONFIG_GLOBAL=$PWD/test-gitconfig; sh out/git-proxy.sh; git clone -q http://demo.test:26082/demo.git clone; git -C clone log --oneline
e54eb27 first commit
$ npm --userconfig out/npmrc --cache ./npmcache view demo-pkg version --registry http://demo.test:26082/
1.0.0
$ PIP_CONFIG_FILE=out/pip.conf python3 -m pip index versions demo-pkg --index-url http://demo.test:26082/simple/ --trusted-host demo.test --disable-pip-version-check 2>/dev/null
demo-pkg (1.1.0)
Available versions: 1.1.0, 1.0.0
$ python3 -m json.tool out/docker-daemon.json >/dev/null && python3 -m json.tool out/docker-config.json >/dev/null && echo "JSON ok"
JSON ok
```

The proxy's log confirms that every request arrived with the right login:

```text
10:55:37.516 http   127.0.0.1:61251 GET http://demo.test:26082/hello.txt auth=ok -> forwarded
10:55:37.526 http   127.0.0.1:61253 GET http://demo.test:26082/hello.txt auth=ok -> forwarded
10:55:37.564 http   127.0.0.1:61255 GET http://demo.test:26082/hello.txt auth=ok -> forwarded
10:55:37.594 http   127.0.0.1:61257 GET http://demo.test:26082/demo.git/info/refs?service=git-upload-pack auth=missing -> 407
10:55:37.595 http   127.0.0.1:61257 GET http://demo.test:26082/demo.git/info/refs?service=git-upload-pack auth=ok -> forwarded
10:55:37.625 http   127.0.0.1:61259 GET http://demo.test:26082/demo.git/HEAD auth=ok -> forwarded
10:55:37.628 http   127.0.0.1:61261 GET http://demo.test:26082/demo.git/objects/e5/4eb2751bf9c046c8dae05516c8e077e6bd5787 auth=ok -> forwarded
10:55:37.759 http   127.0.0.1:61263 GET http://demo.test:26082/npm auth=ok -> forwarded
10:55:37.760 http   127.0.0.1:61264 GET http://demo.test:26082/demo-pkg auth=ok -> forwarded
10:55:37.764 http   127.0.0.1:61267 GET http://demo.test:26082/npm auth=ok -> forwarded
10:55:38.018 http   127.0.0.1:61271 GET http://demo.test:26082/simple/demo-pkg/ auth=ok -> forwarded
```

git's first request went out without the login, got a 407, and was repeated with it on the same connection; that is normal for git. The `/npm` lines are npm checking for its own update. Not run here: PowerShell, and Docker itself (only the JSON was checked).

The same test with `socks5h://` input: curl (`curlrc` and `ALL_PROXY`), git (`http.proxy`, and `ALL_PROXY` alone) and npm 11.9 all went through the SOCKS5 side with the right login. pip 21.2 stopped with `Missing dependencies for SOCKS support.`, httpx with `the 'socksio' package is not installed`, and Node's `fetch` ignored `ALL_PROXY` and went direct. For Docker the script prints nothing for SOCKS5.

## Why each format needs its own escaping

| Where | What breaks without care |
|---|---|
| Any proxy URL | `@ : / # ? %` in the password end the username, the host or the URL early. Percent-encode them: `@` is `%40`, `#` is `%23`, `:` is `%3A`, `/` is `%2F`, `%` is `%25` |
| systemd unit files (Docker drop-in) | `%` starts a systemd specifier, so the encoded `%40` must be written `%%40` |
| bash and zsh | Characters such as `$`, `!` and spaces need quoting; after percent-encoding, a proxy URL has none of them |
| PowerShell | Single quotes keep the value literal; a `'` inside is doubled |
| `~/.curlrc` | Values in double quotes treat `\` and `"` as escapes |
| npmrc, pip.conf, JSON | Fine as long as the URL is percent-encoded. pip reads its file without `%` interpolation, so `%40` stays as it is |

## Related

- [proxy-password-special-characters](https://github.com/proxy302/proxy-password-special-characters): the encoding rules, tested in curl, httpx and aiohttp
- [proxy-env-check](https://github.com/proxy302/proxy-env-check): which proxy your shell's tools will really use
- [How do I make git clone and push go through a proxy?](https://github.com/proxy302/proxy-guides/blob/main/git-proxy/README.md)
- [How do I use npm behind a proxy?](https://github.com/proxy302/proxy-guides/blob/main/npm-proxy/README.md)

*Checked 26 November 2026.*
