#!/usr/bin/env python

import cmd
import getpass
import json
import os
import random
import string
import subprocess
import sys


class Pw(cmd.Cmd, object):

    def __init__(self, path):
        super(Pw, self).__init__()
        self.path = path
        self.data = {}
        self.key = None
        self.identchars = string.letters + string.digits + string.punctuation
        self.prompt = '> '
        self.undoc_header = 'Commands:'
        self.ruler = None


    def preloop(self):
        if os.path.exists(self.path):
            while True:
                self.key = getpass.getpass('Password: ')
                if self.load_data():
                    break
        else:
            self.define_key()
            self.save_data()

        try:
            import readline
            self.old_completer_delims = readline.get_completer_delims()
            readline.set_completer_delims(string.whitespace)
        except ImportError:
            pass


    def postloop(self):
        if hasattr(self, 'old_completer_delims'):
            readline.set_completer_delims(self.old_completer_delims)


    def default(self, s):
        if s == 'EOF':
            print
            sys.exit(0)
        else:
            self.do_help(None)


    def emptyline(self):
        pass


    def do_help(self, s):
        super(Pw, self).do_help(None)


    def do_passwd(self, s):
        self.define_key()
        self.save_data()


    def do_add(self, s):
        s = s.split(None, 3)
        if len(s) < 3:
            self.print_err('Usage: add <id> <user> <password> [note]')
            return
        if s[0] in self.data:
            self.print_err('Id exists!')
            return
        self.data[s[0]] = [s[1], s[2], s[3] if len(s) > 3 else '']
        self.save_data()


    def do_edit(self, s):
        s = s.split(None, 2)
        if len(s) != 2:
            self.print_err('Usage: edit <id> <new password>')
            return
        if s[0] not in self.data:
            self.print_err('Not found!')
            return
        if self.confirm():
            self.data[s[0]][1] = s[1]
            self.save_data()


    def complete_edit(self, text, line, begidx, endidx):
        return self.find_ids(text, line, begidx, endidx)


    def do_get(self, s):
        if not s:
            self.print_err('Usage: get <id>')
            return
        self.get(s, show=False)


    def complete_get(self, text, line, begidx, endidx):
        return self.find_ids(text, line, begidx, endidx)


    def do_show(self, s):
        if not s:
            self.print_err('Usage: show <id>')
            return
        self.get(s, show=True)


    def complete_show(self, text, line, begidx, endidx):
        return self.find_ids(text, line, begidx, endidx)


    def do_del(self, s):
        if not s:
            self.print_err('Usage: del <id>')
            return
        if s not in self.data:
            self.print_err('Not found!')
            return
        if self.confirm():
            del self.data[s]
            self.save_data()


    def complete_del(self, text, line, begidx, endidx):
        return self.find_ids(text, line, begidx, endidx)


    def do_gen0(self, s):
        try:
            self.gen(s, punct=False)
        except ValueError:
            self.print_err('Usage: gen0 <length>')
            return


    def do_gen(self, s):
        try:
            self.gen(s, punct=True)
        except ValueError:
            self.print_err('Usage: gen <length>')
            return


    def find_ids(self, text, line, begidx, endidx):
        argc = len(line.split()) - 1
        if argc > 1 or argc == 1 and begidx == endidx:
            return []
        return filter(lambda x: x.startswith(text), self.data.keys())


    def gen(self, size, punct=True):
        size = int(size)
        if size < 1:
            raise ValueError()
        charset = string.ascii_letters + string.digits
        if punct:
            charset += string.punctuation
        key = ''
        for _ in range(size):
            key += random.choice(charset)
        self.print_out(key)
        self.copy_to_clipboard(key)


    def get(self, idx, show=False):
        if idx not in self.data:
            self.print_err('Not found!')
            return
        user, passwd, note = self.data[idx]
        s = user
        if show:
            s += ' : ' + passwd
        else:
            s += ' : ******'
        if note:
            s += ' | ' + note
        self.print_out(s)
        self.copy_to_clipboard(passwd)


    def define_key(self):
        while True:
            newkey = getpass.getpass('Enter new password: ')
            if not newkey.strip():
                continue
            repeat = getpass.getpass('Repeat new password: ')
            if newkey == repeat:
                self.key = newkey
                return
            self.print_err('Does not match!')


    def save_data(self):
        p = subprocess.Popen([
            'openssl', 'enc', '-e', '-aes-256-cbc',
            '-pbkdf2', '-iter', '100000',
            '-pass', 'stdin', '-out', self.path
        ], stdin=subprocess.PIPE)

        p.communicate(self.key + '\n' + json.dumps(
            self.data,
            sort_keys=True,
            indent=4,
            separators=(',', ': ')
        ))


    def load_data(self):
        p = subprocess.Popen([
            'openssl', 'enc', '-d', '-aes-256-cbc',
            '-pbkdf2', '-iter', '100000',
            '-pass', 'stdin', '-in', self.path
        ], stdin=subprocess.PIPE, stdout=subprocess.PIPE)

        stdout, _ = p.communicate(self.key)

        if p.returncode != 0:
            return False

        self.data = json.loads(stdout)
        return True


    def confirm(self):
        while True:
            ans = raw_input('Are you sure? (y/n): ')
            if ans == 'n':
                return False
            if ans == 'y':
                return True


    def print_out(self, s):
        print '\x1b[32m%s\x1b[0m' % s


    def print_err(self, s):
        print '\x1b[31m%s\x1b[0m' % s


    def copy_to_clipboard(self, s):
        subprocess.Popen(['xsel'], stdin=subprocess.PIPE).communicate(s)
        subprocess.Popen(['xsel', '-b'], stdin=subprocess.PIPE).communicate(s)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        path = os.getenv('HOME') + '/.pw.json.enc'
    else:
        path = sys.argv[1]
    try:
        Pw(path).cmdloop()
    except KeyboardInterrupt:
        print
        pass
