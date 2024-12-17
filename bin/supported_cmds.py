import sys

from collections import OrderedDict, namedtuple

from pyipmi.msgs.registry import DEFAULT_REGISTRY


def make_table(grid):
    col_length = map(list, zip(*[[len(item) for item in row] for row in grid]))
    max_cols = [max(out) for out in col_length]
    rst = table_div(max_cols, 1)

    for i, row in enumerate(grid):
        header_flag = False
        if i == 0 or i == len(grid)-1:
            header_flag = True
        rst += normalize_row(row, max_cols)
        rst += table_div(max_cols, header_flag)
    return rst


def table_div(max_cols, header_flag=1):
    out = ""
    if header_flag == 1:
        style = "="
    else:
        style = "-"

    for max_col in max_cols:
        out += max_col * style + " "

    out += "\n"
    return out


def normalize_row(row, max_cols):
    r = ""
    for i, max_col in enumerate(max_cols):
        r += row[i] + (max_col - len(row[i]) + 1) * " "

    return r + "\n"


def get_command_list():
    data = list()
    Command = namedtuple('Command', ['netfn', 'cmdid', 'grpext', 'name'])

    od = OrderedDict(sorted(DEFAULT_REGISTRY.registry.items()))

    for key, val in od.items():
        if isinstance(key, tuple):

            # skip response messages
            if key[0] & 1:
                continue

            data.append(Command(str(hex(key[0])), str(hex(key[1])),
                        str(key[2]), val.__name__[:-3]))

    return data


def main():
    data = get_command_list()
    data.insert(0, ('Netfn', 'CMD', 'Group Extension', 'Name'))

    if len(sys.argv) > 1 and sys.argv[1].lower() == 'rst':
        rst = make_table(data)
        print(rst)
    else:
        print(data)


if __name__ == '__main__':
    main()
