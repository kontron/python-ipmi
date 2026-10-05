import sys

from collections import OrderedDict, namedtuple

from pyipmi.msgs.dcmi import DCMI_GROUP_CODE
from pyipmi.msgs.picmg import PICMG_IDENTIFIER
from pyipmi.msgs.registry import DEFAULT_REGISTRY
from pyipmi.msgs.vita import GROUP_EXTENSION_VSO

GROUP_EXTENSION_NAMES = {
    None: '',
    PICMG_IDENTIFIER: 'PICMG',
    GROUP_EXTENSION_VSO: 'VITA',
    DCMI_GROUP_CODE: 'DCMI',
}


def make_table(grid):
    col_length = map(list, zip(*[[len(item) for item in row] for row in grid], strict=False))
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
    Command = namedtuple('Command',
                         ['netfn', 'cmdid', 'grpext', 'grpext_name', 'name'])

    # the registry holds both name and (netfn, cmdid, grpext) keys; only
    # the tuple keys are of interest here. grpext can be None.
    items = [(key, val) for key, val in DEFAULT_REGISTRY.registry.items()
             if isinstance(key, tuple)]
    od = OrderedDict(sorted(
        items, key=lambda kv: (-1 if kv[0][2] is None else kv[0][2],
                               kv[0][0], kv[0][1])))

    for key, val in od.items():
        # skip response messages
        if key[0] & 1:
            continue

        netfn, cmdid, grpext = key
        grpext_str = '' if grpext is None else hex(grpext)
        grpext_name = GROUP_EXTENSION_NAMES.get(grpext, 'Unknown')
        data.append(Command(hex(netfn), hex(cmdid), grpext_str, grpext_name,
                            val.__name__[:-3]))

    return data


def main():
    data = get_command_list()
    data.insert(0, ('Netfn', 'CMD', 'Group Extension', 'Group Extension Name',
                    'Name'))

    if len(sys.argv) > 1 and sys.argv[1].lower() == 'rst':
        rst = make_table(data)
        print(rst)
    else:
        print(data)


if __name__ == '__main__':
    main()
