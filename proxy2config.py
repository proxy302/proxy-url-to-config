#!/usr/bin/env python3
"""proxy2config.py: turn one proxy into ready-to-paste settings for curl, shell
variables, git, npm, pip and Docker, with the password escaped the way each one needs.

Python 3.8+, standard library only. Never connects anywhere.
Maintained by Proxy302 (https://proxy302.com). MIT licensed.
"""
import argparse
import json
import os
import shlex
import sys
from urllib.parse import quote, unquote, urlsplit

SECTIONS = ("curl", "env", "git", "npm", "pip", "docker")
SCHEMES = ("http", "socks5h", "socks5")


class Spec:
    pass


def parse(text, default_scheme):
    """Accepts scheme://user:pass@host:port, host:port:user:pass, user:pass@host:port or host:port."""
    s = Spec()
    text = text.strip()
    if "://" in text:
        u = urlsplit(text)
        s.scheme = u.scheme.lower()
        if u.path not in ("", "/") or u.query or u.fragment:
            raise SystemExit("The URL has a path, '?' or '#' in it. If the password contains # / or ?, "
                             "pass it in the form host:port:user:pass instead, and the script will encode it.")
        try:
            port = u.port
        except ValueError:
            raise SystemExit("Could not read the port. If the password contains ':' or '@', use host:port:user:pass.")
        s.host, s.port = u.hostname, port
        s.user = unquote(u.username) if u.username is not None else None
        s.password = unquote(u.password) if u.password is not None else None
    else:
        s.scheme = default_scheme
        parts = text.split(":", 3)
        if len(parts) == 4 and parts[1].isdigit():
            host, port, user, pw = parts          # host:port:user:pass (the password may hold : and @)
        elif "@" in text:
            cred, _, hp = text.rpartition("@")    # user:pass@host:port
            user, _, pw = cred.partition(":")
            host, _, port = hp.rpartition(":")
        elif len(parts) == 2:
            host, port, user, pw = parts[0], parts[1], None, None
        else:
            raise SystemExit("Expected host:port:user:pass, user:pass@host:port or a proxy URL.")
        if not port.isdigit():
            raise SystemExit("The port %r is not a number." % port)
        s.host, s.port, s.user, s.password = host.strip("[]"), int(port), user, pw
    if s.scheme == "socks5h" or s.scheme == "socks5":
        pass
    elif s.scheme == "https":
        print("note: an https:// proxy URL means TLS to the proxy itself. Most HTTP proxies do not speak TLS "
              "on their port and need http://, even for https sites.", file=sys.stderr)
    elif s.scheme != "http":
        raise SystemExit("Unsupported scheme %r. Use http, socks5h or socks5." % s.scheme)
    if not s.host or not s.port:
        raise SystemExit("A host and a port are required.")
    return s


def build_url(s, mask=False):
    host = "[%s]" % s.host if ":" in s.host else s.host
    cred = ""
    if s.user is not None:
        cred = quote(s.user, safe="")
        if s.password is not None:
            cred += ":" + ("****" if mask else quote(s.password, safe=""))
        cred += "@"
    return "%s://%s%s:%d" % (s.scheme, cred, host, s.port)


def ps_quote(v):
    return "'" + v.replace("'", "''") + "'"


def curlrc_quote(v):
    return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'


def systemd_value(v):
    # systemd treats % as a specifier and \ and " as escapes inside "..."
    return v.replace("%", "%%").replace("\\", "\\\\").replace('"', '\\"')


def generate(s, no_proxy):
    url = build_url(s)
    socks = s.scheme.startswith("socks")
    q = shlex.quote
    out = {}  # section -> list of (heading, filename or None, text)

    out["curl"] = [
        ("One request", None, "curl -x %s https://api.ipify.org" % q(url)),
        ("~/.curlrc (or any file passed with curl -K FILE)", "curlrc",
         "proxy = %s\nnoproxy = %s" % (curlrc_quote(url), curlrc_quote(no_proxy))),
    ]

    if socks:
        env_sh = ("export ALL_PROXY=%s\nexport all_proxy=\"$ALL_PROXY\"\n"
                  "export NO_PROXY=%s\nexport no_proxy=\"$NO_PROXY\"" % (q(url), q(no_proxy)))
        env_note = ("curl and git read ALL_PROXY. Python's requests and httpx read it too, but only work with a SOCKS "
                    "URL once their extras are installed (requests[socks], httpx[socks]). Node's built-in fetch ignores ALL_PROXY.")
        env_ps = "$env:ALL_PROXY = %s\n$env:NO_PROXY = %s" % (ps_quote(url), ps_quote(no_proxy))
    else:
        env_sh = ("export http_proxy=%s\nexport https_proxy=\"$http_proxy\"\n"
                  "export HTTP_PROXY=\"$http_proxy\" HTTPS_PROXY=\"$http_proxy\"\n"
                  "export no_proxy=%s\nexport NO_PROXY=\"$no_proxy\"" % (q(url), q(no_proxy)))
        env_note = ("Both spellings on purpose: curl reads only lower-case http_proxy, other tools read upper case. "
                    "HTTPS_PROXY also starts with http:// because it names the proxy, not the site.")
        env_ps = ("$env:HTTP_PROXY = %s\n$env:HTTPS_PROXY = %s\n$env:NO_PROXY = %s"
                  % (ps_quote(url), ps_quote(url), ps_quote(no_proxy)))
    out["env"] = [
        ("bash / zsh (paste into the shell, or into ~/.bashrc or ~/.zshrc)", "proxy-env.sh", env_sh),
        ("PowerShell (this window only)", "proxy-env.ps1", env_ps),
        ("Note", None, env_note),
    ]

    out["git"] = [
        ("All https:// remotes", "git-proxy.sh", "git config --global http.proxy %s" % q(url)),
        ("Only one host", None, "git config --global http.https://github.com.proxy %s" % q(url)),
        ("Note", None, "There is no https.proxy key in git: http.proxy covers https:// remotes too. "
                       "Remotes written as git@host:repo use SSH and ignore it. "
                       "Undo with: git config --global --unset http.proxy"),
    ]

    npmrc = "proxy=%s\nhttps-proxy=%s\nnoproxy=%s" % (url, url, no_proxy)
    out["npm"] = [
        ("Commands", None, "npm config set proxy %s\nnpm config set https-proxy %s\nnpm config set noproxy %s"
         % (q(url), q(url), q(no_proxy))),
        ("or these lines in ~/.npmrc", "npmrc", npmrc),
    ]
    if socks:
        out["npm"].append(("Note", None, "npm 10 and 11 accept socks5h:// and socks5:// here (checked with npm 11.9)."))

    pip_conf = "[global]\nproxy = %s" % url
    out["pip"] = [
        ("Command", None, "pip config set global.proxy %s" % q(url)),
        ("or pip.conf (Linux ~/.config/pip/pip.conf, macOS ~/Library/Application Support/pip/pip.conf, "
         "Windows %APPDATA%\\pip\\pip.ini)", "pip.conf", pip_conf),
        ("One install only", None, "pip install --proxy %s PACKAGE" % q(url)),
    ]
    if socks:
        out["pip"].append(("Note", None, "pip needs the PySocks package for SOCKS; without it pip stops with "
                                         "\"Missing dependencies for SOCKS support\". An HTTP proxy needs nothing extra."))

    if socks:
        out["docker"] = [("Note", None, "Docker's proxy documentation covers HTTP and HTTPS proxies. "
                                        "Use an HTTP proxy for Docker; nothing generated for SOCKS.")]
    else:
        daemon = {"proxies": {"http-proxy": url, "https-proxy": url, "no-proxy": no_proxy}}
        client = {"proxies": {"default": {"httpProxy": url, "httpsProxy": url, "noProxy": no_proxy}}}
        dropin = "[Service]\n" + "\n".join(
            'Environment="%s=%s"' % (k, systemd_value(v))
            for k, v in (("HTTP_PROXY", url), ("HTTPS_PROXY", url), ("NO_PROXY", no_proxy)))
        out["docker"] = [
            ("Image pulls: /etc/docker/daemon.json, then restart Docker (merge into an existing file)",
             "docker-daemon.json", json.dumps(daemon, indent=2)),
            ("or a systemd drop-in: /etc/systemd/system/docker.service.d/http-proxy.conf "
             "(then: sudo systemctl daemon-reload && sudo systemctl restart docker)",
             "docker-http-proxy.conf", dropin),
            ("Containers and docker build: ~/.docker/config.json (merge into an existing file)",
             "docker-config.json", json.dumps(client, indent=2)),
            ("Note", None, "In the systemd file every % is doubled, because systemd reads % as a specifier. "
                           "Values in ~/.docker/config.json become environment variables inside your containers, "
                           "where anyone who can inspect the container can read the password. "
                           "Docker Desktop has its own setting: Settings > Resources > Proxies."),
        ]
    return out


def main(argv):
    ap = argparse.ArgumentParser(description="Print ready-to-paste proxy settings for curl, env vars, git, npm, pip and Docker.")
    ap.add_argument("proxy", help="http://USER:PASS@HOST:PORT, socks5h://..., HOST:PORT:USER:PASS or USER:PASS@HOST:PORT")
    ap.add_argument("--scheme", choices=SCHEMES, default="http", help="scheme for input without one (default http)")
    ap.add_argument("--no-proxy", default="localhost,127.0.0.1,::1",
                    help="hosts that should skip the proxy (default localhost,127.0.0.1,::1)")
    ap.add_argument("--only", help="comma-separated sections: " + ",".join(SECTIONS))
    ap.add_argument("--write", metavar="DIR", help="also write each config into its own file in DIR")
    a = ap.parse_args(argv)

    s = parse(a.proxy, a.scheme)
    wanted = SECTIONS if not a.only else [x.strip() for x in a.only.split(",")]
    for w in wanted:
        if w not in SECTIONS:
            raise SystemExit("unknown section %r; choose from %s" % (w, ", ".join(SECTIONS)))
    out = generate(s, a.no_proxy)

    print("proxy     %s" % build_url(s, mask=True))
    if s.user is not None:
        print("username  %r, password %d characters, both percent-encoded below" % (s.user, len(s.password or "")))
    print("no_proxy  %s" % a.no_proxy)
    titles = {"curl": "curl", "env": "Environment variables", "git": "git", "npm": "npm", "pip": "pip", "docker": "Docker"}
    for sec in wanted:
        print("\n== %s" % titles[sec])
        for heading, fname, text in out[sec]:
            print("\n%s:" % heading if heading != "Note" else "")
            if heading == "Note":
                print("# " + text)
            else:
                print("\n".join("    " + line for line in text.splitlines()))
    if a.write:
        os.makedirs(a.write, exist_ok=True)
        written = []
        for sec in wanted:
            for _, fname, text in out[sec]:
                if fname:
                    path = os.path.join(a.write, fname)
                    with open(path, "w") as f:
                        f.write(text + "\n")
                    os.chmod(path, 0o600)
                    written.append(fname)
        print("\nwrote %s to %s (mode 600, they contain the password)" % (", ".join(written), a.write))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
