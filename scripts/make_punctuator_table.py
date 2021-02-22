#! /usr/bin/env python
#
#  Creates a possibly faster lookup table for tokens, etc.
#
# @author  Ben Gardner
# @author  Matthew Woehlke
# @license GPL v2+
#
import argparse
import os
import sys


# -----------------------------------------------------------------------------
def scan_file(file_path):
    cur_token = ''
    token_idx = 0
    args = []

    fd = open(file_path, 'r')
    for line in fd:
        line = line.strip()
        if line.startswith('static const chunk_tag_t'):
            idx = line.find('[')
            if idx > 0:
                cur_token = line[25:idx].strip()
                token_idx = 0
        else:
            if len(cur_token) > 0:
                idx1 = line.find('{')
                idx2 = line.find('CT_')
                if idx1 >= 0 and idx2 > idx1:
                    tok = line[idx1 + 1:idx2].strip()
                    if tok.startswith('R"'):
                        pos_paren_open = tok.find('(')
                        pos_paren_close = tok.rfind(')')

                        if pos_paren_open == -1 or pos_paren_close == -1:
                            sys.stderr.write(
                                'raw string parenthesis not found\n')
                            sys.exit(-1)

                        tok = tok[pos_paren_open + 1:pos_paren_close]
                    else:
                        tok = tok[1:-2]  # strip off open quotes and commas
                    args.append([tok, '%s[%d]' % (cur_token, token_idx)])
                    token_idx += 1
    return args


# -----------------------------------------------------------------------------
def build_table(db, prev, arr):
    # do the current level first
    k = sorted(db)
    if len(k) <= 0:
        return
    k.sort()

    start_idx = len(arr)
    num_left = len(k)

    for i in k:
        en = db[i]
        # [ char, full-string, left-in-group, next_index, table-entry ]
        num_left -= 1
        arr.append([en[0], prev + en[0], num_left, 0, en[2]])

    # update the one-up level index
    if len(prev) > 0:
        for idx in range(0, len(arr)):
            if arr[idx][1] == prev:
                arr[idx][3] = start_idx
                break

    # Now do each sub level
    for i in k:
        en = db[i]
        build_table(en[3], prev + en[0], arr)


# -----------------------------------------------------------------------------
def add_to_db(entry, db_top):
    """
    find or create the entry for the first char
    """
    strng = entry[0]
    db_cur = db_top
    for idx in range(0, len(strng)):
        if not strng[idx] in db_cur:
            db_cur[strng[idx]] = [strng[idx], 0, None, {}]

        dbe = db_cur[strng[idx]]

        if idx == len(strng) - 1:
            dbe[2] = entry
        else:
            db_cur = dbe[3]


# -----------------------------------------------------------------------------
def quote(s):
    return '\'{}\''.format(s)


# -----------------------------------------------------------------------------
def escape(s):
    return quote(s.replace('\'', '\\\''))


# -----------------------------------------------------------------------------
def write_entry(out, max_len, ch, left_in_group, next_idx, tag, idx, tok):
    out.write('   {{ {:>4}, {:>3d}, {:>3d}, {:{}} }},  // {:3d}: {}'.format(
        ch, left_in_group, next_idx, tag, max_len, idx, tok).rstrip())
    out.write('\n')


# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description='Generate punctuator_table.h')
    parser.add_argument('output',
                        type=str,
                        help='location of punctuator_table.h to write')
    parser.add_argument('header',
                        type=str,
                        help='location of symbols_table.h to read')
    args = parser.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pl = scan_file(args.header)
    pl.sort()

    db = {}
    for a in pl:
        add_to_db(a, db)

    arr = []
    build_table(db, '', arr)

    max_len = len('nullptr')
    for i in arr:
        rec = i[4]
        if rec is not None and (len(rec[1]) + 1) > max_len:
            max_len = len(rec[1]) + 1

    in_name = os.path.basename(args.header)
    out_name = os.path.basename(args.output)
    guard = out_name.replace('.', '_').upper()

    with open(args.output, 'wt') as out:
        out.write('/**\n'
                  ' * @file {out_name}\n'
                  ' * Automatically generated by <code>{script}</code>\n'
                  ' * from {in_name}.\n'
                  ' */\n'
                  '\n'
                  '#ifndef SRC_{guard}_\n'
                  '#define SRC_{guard}_\n'
                  '\n'
                  '// *INDENT-OFF*\n'
                  'static const lookup_entry_t punc_table[] =\n'
                  '{{\n'.format(in_name=in_name,
                                out_name=out_name,
                                guard=guard,
                                script=os.path.relpath(__file__, root)))

        idx = 0

        for i in arr:
            rec = i[4]
            if len(i[0]) == 0:
                write_entry(out, max_len, '0', '0', '0', 'nullptr', idx, '')
            elif rec is None:
                write_entry(out, max_len, escape(i[0]), i[2], i[3], 'nullptr',
                            idx, quote(i[1]))
            else:
                write_entry(out, max_len, escape(i[0]), i[2], i[3],
                            '&' + rec[1], idx, quote(i[1]))
            idx += 1

        out.write('}};\n'
                  '// *INDENT-ON*\n'
                  '\n'
                  '#endif /* SRC_{guard}_ */\n'.format(guard=guard))


# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

if __name__ == '__main__':
    main()
