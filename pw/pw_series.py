# SPDX-License-Identifier: GPL-2.0
#
# Copyright (C) 2019 Netronome Systems, Inc.

import re

from core import Series
from core import Patch
from core import log, log_open_sec, log_end_sec

# TODO: document


class PwSeries(Series):
    def __init__(self, pw, pw_series):
        super().__init__(ident=pw_series['id'])

        self.pw = pw
        self.pw_series = pw_series

        if pw_series['cover_letter']:
            pw_cover_letter = pw.get_mbox('cover',
                                          pw_series['cover_letter']['id'])
            self.set_cover_letter(pw_cover_letter.text)
        elif self.pw_series['patches']:
            self.subject = self.pw_series['patches'][0]['name']
            self.title = self.pw_series['patches'][0]['name']
        else:
            self.subject = ""
            self.title = ""

        # Add patches to series
        # Patchwork 2.2.2 orders them by arrival time
        pids = []
        for p in self.pw_series['patches']:
            pids.append(p['id'])
        total = self.pw_series['total']
        if total == len(self.pw_series['patches']):
            for i in range(total):
                name = self.pw_series['patches'][i]['name']
                pid = self.pw_series['patches'][i]['id']
                for j in range(total):
                    if name.find(f" {j + 1}/{total}") >= 0 or \
                       name.find(f"0{j + 1}/{total}") >= 0:
                        if pids[j] != pid:
                            log(f"Patch order - reordering {i} => {j + 1}")
                            pids[j] = pid
                        break
        else:
            log("Patch order - count does not add up?!", "")

        for pid in pids:
            raw_patch = pw.get_mbox('patch', pid)
            self.patches.append(Patch(raw_patch.text, pid))

        if not pw_series['cover_letter'] and self.patches:
            self.fixup_pull_covers()

    def __getitem__(self, key):
        return self.pw_series[key]

    def fixup_pull_covers(self):
        # For pull requests posted as series patchwork treats the cover letter
        # as a patch so the cover is null. Try to figure that out but still
        # use first patch for prefix, pulls don't have dependable subjects.
        all_reply = None

        log_open_sec("Searching for implicit cover/pull request")
        for p in self.patches:
            lines = p.raw_patch.split('\n')
            r_in_reply = re.compile(r'^In-Reply-To: <(.*)>$')
            reply_to = None

            for line in lines:
                if line == "":  # end of headers
                    if reply_to is None:
                        log("Patch had no reply header", "")
                        all_reply = False
                    break
                match = r_in_reply.match(line)
                if not match:
                    continue

                reply_to = match.group(1)
                log("Patch reply header", reply_to)
                if all_reply is None:
                    all_reply = reply_to
                elif all_reply != reply_to:
                    all_reply = False
                    log("Mismatch in replies", "")
        log("Result", all_reply)
        log_end_sec()
