import sys

cnf_filename = sys.argv[1]
min = ''
max = ''
with open(cnf_filename) as f:
    print('PB変数とCNFファイルの対応情報を読み込み中...')
    for line in f:
        lineblock = line.split()
        if lineblock!=[]:
            if (lineblock[0]=='cv'):
                lineblock.pop(0)
                for i in lineblock:
                    var_block=i.split(':')
                    if 'P1' in var_block[1]:
                        min += '1 ' + str(var_block[1]) +' '
                    elif 'P0' in var_block[1]:
                        max += '1 ' + str(var_block[1]) +' '
    print(min)
    print(max)
#最適化問題として解くために変数を抽出するためのプログラム
