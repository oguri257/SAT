##
## 正方形ベースの Rep-tile の Pseudo Boolean 制約生成ライブラリ
##
## 特定の問題に特化した制約生成プログラムは以下のようにする
##-----------------------------------------------------------------------------
## imprt rev					# このファイルをインポート
##
## UsageText ="ヘルプコメントをここに書く"   #(省略可)
##
## MinBoard = {(x1, y1), .... , (xn, yn)}	# サイズ１の枠の座標を書く
## #  例 MinBoard = {(0, 0), (0, 1), (0, 2), (1, 1), (1, 2), (2, 2)}
##
## PrimTilePat = [ (1, MinBoard) ]		# タイルの定義（通常はサイズ１の枠を使う）
##						# 第１要素はタイルのタイプで
##						# 生成される制約変数の P?(xxxxx) の？に使われる
## ## メイン関数
## if __name__ == "__main__":
##     rev.gen_reptile(MinBoard, PrimTilePat, UsageText)
##-----------------------------------------------------------------------------

import sys
import os
import shutil
import time
import argparse
import textwrap
import re

##
## 配置領域（の設定関数）:
##   MinBoard（サイズ m,n とする） N倍の領域に許可(True)・禁止(False)を設定．
##   D は (m*N+maxlen)行(n*N+maxlen)列 だが，外側は常に禁止領域．
##   サイズパラメータ N はコマンドライン引数で与える．
def setDomain(D, N, pat):
    #    M = pat.xlen() * N

    for (x, y) in pat.cells:
        for i in range(N):
            for j in range(N):
                D[N * x + i][N * y + j] = True

################################################################################
################################################################################

##
## Tileクラス: ボードに埋め込まれたタイル
##
class Tile(object):
    def __init__(self, cells, type=0):
        super().__init__()
        self.cells = set(cells)
        self.size = len(cells)
        self.type = type

        setX = {x for (x, y) in cells}
        setY = {y for (x, y) in cells}
        if self.size > 0:
            self.xmin = min(setX)
            self.xmax = max(setX)
            self.ymin = min(setY)
            self.ymax = max(setY)
        else:
            self.xmin = 0
            self.xmax = -1
            self.ymin = 0
            self.ymax = -1
        self.borders = set()
        for (x,y) in cells:
            for i in range(x-1,x+2,2):
                if not (i, y) in cells:
                    self.borders.add((i, y))
            for j in range(y-1,y+2,2):
                if not (x,j) in cells:
                    self.borders.add((x, j)) #self.bordersに上下左右の点を追加
         #   for i in range(x-1,x+2):
         #       for j in range(y-1,y+2):
         #           if not (i,j) in cells:
         #               self.borders.add((i, j))

    def __str__(self):
        return "P{}({})".format(self.type, ','.join(["(" + str(x) + "," + str(y) + ")" for (x, y) in sorted(self.cells)]))

    def toVariable(self, M):
        return "P{}({})".format(self.type, ','.join([str(p) for p in sorted([y * M + x + 1 for (x, y) in self.cells])]))

    def xlen(self):
        return (self.xmax - self.xmin + 1)

    def ylen(self):
        return (self.ymax - self.ymin + 1)

    # p =(x,y) の位置を占めるか？
    def contains(self, p):
        return (p in self.cells)

    def isnormalized(self):
        return (self.xmin == 0 and self.ymin == 0)

    def isoverlap(self, other):
        if not isinstance(other, Tile):
            return false
        return (not (self.cells.isdisjoint(other.cells)))#self.cellsとother.cellsが互いに素の時true これにnotがついてる　重なりが一つでもあればtrue

    # create normalized new Tile
    def normalize(self):
        #        if(self.isnormalized()):
        #            return
        xshift = -self.xmin
        yshift = -self.ymin
        return Tile({(x + xshift, y + yshift) for (x, y) in self.cells}, self.type)

    def xflip(self):
        return Tile({(self.xmax - x, y) for (x, y) in self.cells}, self.type).normalize()

    def rrotate(self):
        return Tile({(-y, x) for (x, y) in self.cells}, self.type).normalize()

    def drotate(self):
        return Tile({(x, -y) for (x, y) in self.cells}, self.type).normalize()

    def __eq__(self, other):
        if not isinstance(other, Tile):
            return False
        return (self.type == other.type and self.cells == other.cells)
        #return self.cells == other.cells　元々のやつ

    def __hash__(self):
        return hash(tuple(self.cells))

##
## PB等式出力用の関数
##
#   1 P0(1,3,4) 1 P0(1,2,3) ...
def printLinEx(out, exp, M):
    for (coeff, tile) in exp:
        print("{} {}".format(coeff, tile.toVariable(M)), end=' ', file=out)

def printConstr(out, exp, M, Op, num):
    if exp != set():
        printLinEx(out, exp, M)
        print("{} {};".format(Op, num), file=out)

def tilesToExp(tileSet, coeff=1):
    res = set()
    for t in tileSet:
        res.add((coeff, t))
    return res
#coeffは係数1

##
## コマンドラインオプション
##
def get_args(UsageText):
    if UsageText == "":
        parser = argparse.ArgumentParser(
            formatter_class=argparse.RawDescriptionHelpFormatter)
    else:
        parser = argparse.ArgumentParser(
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=textwrap.dedent(UsageText))

    parser.add_argument("N", type=int, help="problem size")  # 問題サイズ
    parser.add_argument("--nOC", type=str, help="constraints on rectangle pieces: NOC is >n, >=n, =n, <n or <=n")  # 長方形ピースの使用数の条件
    parser.add_argument("--nOCsimp", action="store_true", help="prefer simple constraints on number of pieces withtout assuming rectangles")
    parser.add_argument("--frm", type=int, help="generates PB files for every rectangle pieces >= n")
    parser.add_argument("--to", type=int, help="generates PB files for every rectangle pieces <= n")
    parser.add_argument("--each", action="store_true", help="generates all PB files for every n rectangle pieces (same as --from 0 --to N*N)")
    parser.add_argument("--min", action="store_true", help="minimizing rectangle pieces")
    parser.add_argument("--max", action="store_true", help="maximizing rectangle pieces")
    parser.add_argument("--opt", choices=['0','1','2'], default=1, help="optimizing level for constraints (default=2)")
    parser.add_argument("--out", type=str, help="output PB file name.  - for standard output")

    args = parser.parse_args()
    if (args.opt == None):
        args.out = 1
    else:
        args.opt = int(args.opt)

    if (args.each):
        args.frm = 0
        args.to = args.N * args.N //2

    if (args.frm != None or args.to != None) and (args.nOC != None or args.min or args.max or args.out):
        print("--each option is not compatible with --nOC, --min, --max, nor --out", file =sys.stderr)
        exit()

    if args.nOC != None:
        m = re.match(r"([><]*[=]?)\s*(\d+)", args.nOC)
        if not m:
            print("possble argument of nOC: >n, >=n, =n, <n, or <=n\n", file=sys.stderr)
            exit()
        args.nOCOp = m.group(1)
        args.nOCNum = int(m.group(2))

    return (args)

## 出力ファイル名の生成
def gen_filename(progName, args):
    resName = "{}-size{}".format(progName, args.N)
    resName = "{}-opt{}".format(resName, args.opt)
    if args.min:
        resName = "{}-rect_min".format(resName)
    if args.max:
        resName = "{}-rect_max".format(resName)

    return resName

## 主関数 MinBoard: サイズ１の枠を座標の集合で表現したもの
##        PrimTilePat: （入れるピースのtype番号と座標の集合の対）の集合
##              type番号: 0 は長方形、１以上はそれ以外の形
def gen_reptile(MinBoard, PrimTilePat, UsageText=""):
    # オプション取得
    args = get_args(UsageText)

    N = args.N
    minBd = Tile(MinBoard)

    if not minBd.isnormalized():
        print("Internal error: minBd is not normalized", file=sys.stderr)
        exit()
    M = N * (minBd.xmax - minBd.xmin + 1)  # ボードの幅
    Mh = N * (minBd.ymax - minBd.ymin + 1)  # ボードの高さ

    # primTilePatのタイルの向きを洗い出して tilePatに入れる
    primTilePat = {Tile(pat, tp) for (tp, pat) in PrimTilePat}
    tilePat = {pat.xflip() for pat in primTilePat} | primTilePat
    tilePat = {pat.drotate() for pat in tilePat} | tilePat
    tilePat = {pat.rrotate() for pat in tilePat} | tilePat

    #    for pat in tilePat:
    #        print("{}".format(pat))
    maxlenx = max({pat.xlen() for pat in tilePat})
    maxleny = max({pat.ylen() for pat in tilePat})
    # maxlen = max(maxlenx,maxleny)

    # 配置領域の設定
    D = [[False for y in range(Mh + maxleny)] for x in range(M + maxlenx)]
    setDomain(D, N, minBd)

    # タイルオブジェクトの生成
    T = [[set() for y in range(Mh)] for x in range(M)]
    H = [[set() for y in range(Mh)] for x in range(M)]
    for i in range(M):
        for j in range(Mh):
            for pat in tilePat:
                m = {(i + x, j + y) for (x, y) in pat.cells}

                # タイルがカバーするマスがすべて許可領域ならば
                # 使用可能なタイルとして登録
                #if not all([ x<M+maxlenx and y<Mh+maxleny for (x,y) in m ]):
                #    print("x")
                if all([D[x][y] for (x, y) in m]):#?????
                    T[i][j].add(Tile(m, pat.type))       # 基本タイルを(i,j)だけ平行移動したタイルを追加
                    for (x,y) in m:
                        H[x][y].add(Tile(m, pat.type))   # (x,y)を埋められるタイルを追加

#Tは標準位置をカバーするタイルを全て含むようになっている
#Hは決めた位置をカバーするタイルを全て含むようになっている

    if args.opt >=1:
        # 端に近いことから配置不能なタイルを調べて T, H から除去
        TD= [[set() for y in range(Mh)] for x in range(M)]
        for i in range(M):
            for j in range(Mh):
                if not D[i][j]:
                    continue
                for tile in T[i][j]:
                    compatible = True
                    for (x,y) in tile.borders:
                        if not D[x][y]:
                            continue
                        if all({ tile3.isoverlap(tile) for tile3 in H[x][y] }):
                            compatible = False
                            break
                    if not compatible:
                        # printConstr(pbOutStream, tileToExp({tile}), M, '=', 0)
                        TD[i][j].add(tile)#おけないタイル集合
        for i in range(M):
            for j in range(Mh):
                if not D[i][j]:
                    continue
                for tile in TD[i][j]:
                    T[i][j].remove(tile)
                    for (x,y) in tile.cells:
                        H[x][y].remove(tile)

    # 出力ファイルの準備
    progName = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    fileNameBase = gen_filename(progName, args)
    if args.out == None or args.out != '-':
        if args.out != None:
            fname = args.out
        else:
            if args.nOC != None:
                resstr = args.nOC.translate(str.maketrans({'<': 'less', '>': 'more', '=': 'equal', }))
                fileNameBase = "{}-rect_{}".format(fileNameBase, resstr)
            fname = "{}.pb".format(fileNameBase)
        pbOutStream = open(fname, 'w')
    else:
        pbOutStream = sys.stdout

    gen_basic_reptile(args, pbOutStream, M, Mh, D, T, H, maxlenx, maxleny)
    primSize = minBd.size
    if args.nOC != None:
        gen_aux_reptile(pbOutStream, M, Mh, T, N, primSize, args.nOCOp, args.nOCNum, args.nOCsimp)
    if args.out == None or args.out != '-':
        pbOutStream.flush()
        os.fsync(pbOutStream.fileno())      # fname が書き込まれるのを待つ
#        time.sleep(1)
        pbOutStream.close

    if (args.frm != None or args.to != None):
        if args.frm == None:
            args.frm = 0
        if args.to == None:
            args.to = N*N//2
        NumRecTile = N*N//2
        for i in range(args.frm, args.to+1):
            newfile = "{}-rect_equal{}.pb".format(fileNameBase, i)
            x = shutil.copyfile(fname, newfile)
            with open(newfile, 'a') as pbOutStream:
                gen_aux_reptile(pbOutStream, M, Mh, T, N, primSize, '=', i)

def gen_basic_reptile(args, pbOutStream, M, Mh, D, T, H, maxlenx, maxleny):

    # 長方形の利用数最大（最小）を求める（オプション）
    if args.max or args.min:
        coeff = 1 if args.min else -1
        print("min:", end=' ', file=pbOutStream)
        cand = set()
        for i in range(M):
            for j in range(Mh):
                for tile in T[i][j]:
                    if 0 == tile.type:
                        cand.add((coeff,tile))
        printLinEx(pbOutStream, cand, M)

    # 制約の生成： 各(i,j)に対して、それを埋めるタイルは一つだけ
    for i in range(M):
        for j in range(Mh):
            if D[i][j]:
                printConstr(pbOutStream, tilesToExp(H[i][j]), M, '=', 1)

    '''
    if args.opt >=2:
        # 制約生成： (i,j) を起点とするタイルと重ならないが同時には配置できないタイル
        for i in range(M):
            for j in range(Mh):
                if not D[i][j]:
                    continue
                for tile in T[i][j]:
                    for k in range(i-maxlenx, i-1):
                        for l in range(j-maxleny, j-1):
                            if k < 0 or l < 0:
                                continue
                            for tile2 in T[k][l]:
                                if tile2.isoverlap(tile):
                                    continue
                                compatible = True
                                for (x,y) in tile.borders or tile2.borders:
                                    if not D[x][y] or tile.contains((x,y)) or tile2.contains((x,y)):
                                        continue
                                    if all({ tile3.isoverlap(tile) or tile3.isoverlap(tile2) for tile3 in H[x][y]}):
                                        #if allだとHの中にあるものの中で一つでも被らないものがあればおk
                                        #全部見てどれも被る物なのであればcompatible=Falseになる
                                        compatible = False
                                        break
　　　　　　　　　　　　　　　　　　　　　#else:
                                   #  printConstr(pbOutStream, tilesToExp({tile, tile2}), M, '<=', 1) tile,tile2が同時に配置可能な文を作りたい
                                   # 一つが確定したのならtile3のおけるもののどちらかが1になるような文を記述　一つが確定する記述とは？
                                if not compatible:
                                    printConstr(pbOutStream, tilesToExp({tile, tile2}), M, '<=', 1)

    if args.opt >=3: #二つおいた時に長方形になるものを取り除くオプション
        for i in range(M):
            for j in range(Mh):
                if not D[i][j]:
                    continue
                for tile in T[i][j]:
                    for k in range(i-maxlenx, i-1):
                        for l in range(j-maxleny, j-1):
                            if k < 0 or l < 0:
                                continue
                    for tile2 in T[k][l]:
                        if tile2.isoverlap(tile):
                            continue
                        compatible = True
                        maxx=i
                        minx=j
                        maxy=k
                        miny=l
                        for (x,y) in tile.borders or tile2.borders:
                            if x>maxx:
                                maxx=x
                            if y>maxy:
                                maxy=y
                            if x<minx:
                                minx=x
                            if y<miny:
                                miny=y
                        if (maxx-minx-1,maxy-miny-1)==(3,4) or (maxx-minx-1,maxy-miny-1)==(4,3):
                            printConstr(pbOutStream, tilesToExp({tile, tile2}), M, '<=', 1)

    '''

    if args.opt >=2: #J型レプタイル問題の時に長方形または斜交いを形成する制約
        for i in range(M):
            for j in range(Mh):
                if not D[i][j]:
                    continue
                for tile in T[i][j]:
                    if not D[i+1][j+1]:
                        printConstr(pbOutStream, tilesToExp(tile), M, '=', 0)
                        break
                    positive_res = set()
                    for tile2 in H[i+1][j+1]:
                        positive_const = True
                        if tile2.isoverlap(tile):
                            continue
                        for (x,y) in (tile.borders | tile2.borders):
                            if not D[x][y] or tile.contains((x,y)) or tile2.contains((x,y)):
                                continue
                            if all({ tile3.isoverlap(tile) or tile3.isoverlap(tile2) for tile3 in H[x][y]}):
                                positive_const = False
                                break
                        if positive_const:
                            positive_res.add((-1, tile))
                            positive_res.add((1, tile2))
                    if not len(positive_res)==0:
                        printConstr(pbOutStream, positive_res, M, '>=', 0)
                        positive_res.discard((-1,tile))
                        printConstr(pbOutStream, positive_res, M, '<=', 1)


def gen_aux_reptile(pbOutStream, M, Mh, T, N, primSize, Op, Num, simp=False):
    # 長方形の利用数に関する制約（オプション）
        rectExp = set()
        nonRectExp = set()
        for i in range(M):
            for j in range(Mh):
                for tile in T[i][j]:
                    if 0 == tile.type:
                        rectExp.add((tile.size//primSize, tile))
                    else:
                        nonRectExp.add((-tile.size//primSize, tile))
        # 長方形の数の制約の出力
        printConstr(pbOutStream, rectExp, M, Op, 2 * Num)
        # 長方形以外の数の制約も出力
        if not simp:
            printConstr(pbOutStream, nonRectExp, M, Op, (2 * Num)-(N*N) )

# for JP fonts
fontsp = ' '
fonthl = '━'
# spaces used below is U+2002
cmapUtf = {(False, False, False, False): '  ', (False,  True, False,  True): '━━', ( True, False,  True, False): '┃ ',
           (False,  True,  True, False): '┏━', (False, False,  True,  True): '┓ ', ( True,  True, False, False): '┗━',
           ( True, False, False,  True): '┛ ', ( True,  True,  True, False): '┣━', ( True, False,  True,  True): '┫ ',
           (False,  True,  True,  True): '┳━', ( True,  True, False,  True): '┻━', ( True,  True,  True,  True): '╋━'}
cmapJp = {(False, False, False, False): '　', (False,  True, False,  True): '━', ( True, False,  True, False): '┃',
          (False,  True,  True, False): '┏', (False, False,  True,  True): '┓', ( True,  True, False, False): '┗',
          ( True, False, False,  True): '┛', ( True,  True,  True, False): '┣', ( True, False,  True,  True): '┫',
          (False,  True,  True,  True): '┳', ( True,  True, False,  True): '┻', ( True,  True,  True,  True): '╋'}

cmapUtfExtra =  ['  ','──','━━','│ ','┃ ','┌─','┍━','┎─','┏━',
    '┐ ','┑ ','┒ ','┓ ','└─','┕━','┖─','┗━','┘ ','┙ ','┚ ','┛ ','├─','┝━','┞─','┟─',
    '┠─','┡━','┢━','┣━','┤ ','┥ ','┦ ','┧ ','┨ ','┩ ','┪ ','┫ ','┬─','┭─','┮━','┯━',
    '┰─','┱─','┲━','┳━','┴─','┵─','┶━','┷━','┸─','┹─','┺━','┻━','┼─','┽─','┾━','┿━',
    '╀─','╁─','╂─','╃─','╄━','╅─','╆━','╇━','╈━','╉─','╊━','╋━']
cmapJpExtra =   ['　','─','━','│','┃','┌','┍','┎','┏',
    '┐','┑','┒','┓','└','┕','┖','┗','┘','┙','┚','┛','├','┝','┞','┟',
    '┠','┡','┢','┣','┤','┥','┦','┧','┨','┩','┪','┫','┬','┭','┮','┯',
    '┰','┱','┲','┳','┴','┵','┶','┷','┸','┹','┺','┻','┼','┽','┾','┿',
    '╀','╁','╂','╃','╄','╅','╆','╇','╈','╉','╊','╋']
def listup(utfMode=False):
    if(utfMode):
        cmap = cmapUtfExtra
    else:
        cmap = cmapJpExtra
    for c in cmap:
        print("'{}'  ".format(c), end='')
    print('')

# (north, east, south, west)
def vec_to_char(p, utfMode=False):
    if(utfMode):
        ch = cmapUtf.get(p)
    else:
        ch = cmapJp.get(p)
    assert (ch != None), "{}".format(p)
    return ch

# Tileの集合を表示する
def draw_tiles(pieces, utfMode, out=sys.stdout):
    xmax = max(p.xmax for p in pieces)
    ymax = max(p.ymax for p in pieces)

    def within(x,y):
        return(0<=x and x<=xmax and 0<=y and y<=ymax)
    def sign(z):
        reuturn(0 if z<0 else 1)

    def add_north(di):
        (n, e, s, w) = di
        return(True,e,s,w)
    def add_east(di):
        (n, e, s, w) = di
        return(n,True,s,w)
    def add_south(di):
        (n, e, s, w) = di
        return(n,e,True,w)
    def add_west(di):
        (n, e, s, w) = di
        return(n,e,s,True)

    Bd = [[ (False,False,False,False) for y in range(ymax+2)] for x in range(xmax+2)]

    for p in pieces:
        for (x,y) in p.cells:
            if (not within(x-1,y)) or (not p.contains((x-1,y))):
                Bd[x][y] = add_south(Bd[x][y])
                Bd[x][y+1] = add_north(Bd[x][y+1])
            if (not within(x+1,y)) or (not p.contains((x+1,y))):
                Bd[x+1][y] = add_south(Bd[x+1][y])
                Bd[x+1][y+1] = add_north(Bd[x+1][y+1])
            if (not within(x,y-1)) or (not p.contains((x,y-1))):
                Bd[x][y] = add_east(Bd[x][y])
                Bd[x+1][y] = add_west(Bd[x+1][y])
            if (not within(x,y+1)) or (not p.contains((x,y+1))):
                Bd[x][y+1] = add_east(Bd[x][y+1])
                Bd[x+1][y+1] = add_west(Bd[x+1][y+1])

    for y in range(ymax+2):
        for x in range(xmax+2):
            print(vec_to_char(Bd[x][y], utfMode), end='', file=out)
        print('', file=out)
    return

#  converting a string p = "ABC((0,0),(0,1),(1,1))" to Tile object
extract_offset = re.compile(r'^[ ]*\[([+-]?\d+),[ ]*([+-]?\d+)\]')
decomop_cells  = re.compile(r'\((\d+),[ ]*(\d+)\)')
def strToTile(p):
    offset    = extract_offset.match(p)
    (ox,oy) = (0,0)
    if offset:
        (ox,oy) = ( int(offset.group(1)), int(offset.group(2)) )
    positions = decomop_cells.findall(p)
    return Tile( { (int(x)+ox,int(y)+oy) for (x,y) in positions } )

def intToVec(m, M):
    return (((m-1) % M, (m-1) // M))

# converting a string p = "ABC(2,3,7)", and M = 5
decomp_cellM = re.compile(r'(\d+)')
def strToTileM(p, M, type=0):
    positions = decomp_cellM.findall(p)
    x = { intToVec(int(m), M) for m in positions }
    return Tile(x, type)
