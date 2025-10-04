#!/usr/bin/env python3

import argparse, time, json, hmac, hashlib, base64, os, sys, shutil, subprocess

def parse_env(path: str) -> str | None:
    secret = None
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("JWT_SECRET"):
                    _, v = line.split("=", 1)
                    v = v.strip().strip('"').strip("'")
                    secret = v
                    break
    except FileNotFoundError:
        return None
    return secret

def b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")

def main():
    ap = argparse.ArgumentParser(description="Generate an admin JWT (HS256) signed with JWT_SECRET from a .env file.")
    ap.add_argument("--env-path", "--env", dest="env_path", default=".env", help="Path to .env containing JWT_SECRET (default: .env)")
    ap.add_argument("--days", type=int, default=7, help="Validity in days (default: 7)")
    ap.add_argument("--sub", default="admin@local", help='JWT "sub" claim (default: admin@local)')
    ap.add_argument("--role", default="admin", help='JWT "role" claim (default: admin)')
    ap.add_argument("--no-clipboard", dest="clipboard", action="store_false", help="Do not copy token to clipboard")
    ap.set_defaults(clipboard=True)
    args = ap.parse_args()

    secret = parse_env(args.env_path)
    if not secret:
        print(f"ERROR: JWT_SECRET not found in {args.env_path}", file=sys.stderr)
        sys.exit(2)

    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": args.sub, "role": args.role, "iat": now, "exp": now + args.days * 24 * 3600}

    seg1 = b64url(json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    seg2 = b64url(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    sig = hmac.new(secret.encode("utf-8"), f"{seg1}.{seg2}".encode("ascii"), hashlib.sha256).digest()
    token = f"{seg1}.{seg2}.{b64url(sig)}"

    print(token)
    if args.clipboard and shutil.which("pbcopy"):
        try:
            subprocess.run(["pbcopy"], input=token.encode("utf-8"), check=True)
            print("(Copied to clipboard)", file=sys.stderr)
        except Exception as e:
            print(f"(Clipboard copy failed: {e})", file=sys.stderr)

if __name__ == "__main__":
    main()
