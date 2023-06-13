import sys
import rev
import re
import time

from enum import Enum

nnfout_filename = sys.argv[1]
cnf_filename = sys.argv[2]

class NType(Enum):
    LIT   = 0    # リテラル
    OR    = 1    # OR
    AND   = 2    # AND

class Node(object):
    num=0  # 生成したノード数（次に割り当てるid番号）

    def __init__(self,type,lits=None,lit=None):
        self.type = type

        if type == NType.LIT:
            self.lit = lit
        else:
            self.children = lits

        self.id = Node.num
        Node.num += 1
        self.weight = None      ### 斜交いの最大数を求める際に使用する値
        self.branch = None      ### 0:左の子　1:右の子
        self.count=0            ### ノードが持つ解の個数
        #self.weight_list=[]
        self.hasukai=0
        self.odd_even=None
        self.max_branch = None


cor_table = {}      ###{id:[idに該当する元の変数番号]}
return_table = {}   ###{元の変数番号:変数情報}
a = []              ###a行の情報
L_A_O = []          ###L,A,O行の情報
or_stuck = []       ###[[id,LorR]]
started=False       ###関数next_answerで使用する変数
finish=False        ###関数next_answerで使用する変数
# l＿count=0          ###ファイル読み込みの際に各ノードにidを振るために使用する変数
node_list = []      ###各ノードを格納するリスト リストの番目とidが一致するようになっている
answer = []         ###リテラルの正負を格納するリスト　リテラルの絶対値がリストの番目と一致している


def search(node): #ノードを辿っていく関数
    global or_stuck
    #print(node.id)
    if node.type==NType.LIT:
        if node.lit>0:
            answer[abs(node.lit)]=True
        elif node.lit<0:
            answer[abs(node.lit)]=False
        #リテラルを返して解リストを更新
    elif node.type==NType.AND:
        #自分の子供を順に見ていく
        for child in node.children:
            search(node_list[child])
    elif node.type==NType.OR:
        if node.branch == None:
            node.branch = 0
            or_stuck.append(node.id)
            search(node_list[node.children[0]])
        else:
            search(node_list[node.children[node.branch]])

def next_answer(): #順に解を出力するための関数
    global started
    global or_stuck
    global finish
    global answer_number

    if finish==True:
        return
    if started==False:
        search(node_list[-1])
    else:
        while(len(or_stuck)>0 and node_list[or_stuck[-1]].branch==1):
            node_list[or_stuck[-1]].branch = None
            or_stuck.pop()
        if (len(or_stuck)>0):
            node_list[or_stuck[-1]].branch = 1
            search(node_list[-1])
            print(show_answer())
            answer_number += 1
        else:
            # print('no more answer')
            finish=True
    started=True
    #or_stuckの一番上を見る
    #(L) 左の子を見た場合の解を消す
    #    スタックを{id:R}に更新し右の子を見て解く
    #
    #(R) スタックから取り除いて新しいスタックを引数に繰り返す
    #
    #スタックから取り出したものがフラグであれば終了する
    #　　　orノードを見た場合に決まる解を保持する必要あり
    #     orノードの子がLIT->決まる解として保持
    #     orノードの子がAND->ANDが持つ子LITを全てorノードが持つ解として保持



koteians=''
for i in a:
    if i>0:
        koteians = koteians + ' ' + str(return_table.get(abs(i)))
    elif i<0:
        koteians = koteians + ' -' + str(return_table.get(abs(i)))

def show_answer(): #解のリテラル情報を出力する関数
    ans = 'show'
    for i in range(1,len(answer)):
        if answer[i]==True:
            lit = cor_table.get(i)#正リテラルの解を元の変数に戻す　originはリスト
            if lit==None:
                continue
            for j in lit:
                ans=ans+' '+str(return_table.get(j))
            nolit = cor_table.get(-i)
            if nolit==None:
                continue
            for j in nolit:
                ans=ans+' -'+str(return_table.get(j))

        elif answer[i]==False:
            nolit = cor_table.get(-i)
            if nolit==None:
                continue
            for j in nolit:
                ans=ans+' '+str(return_table.get(j))
            lit = cor_table.get(i)#正リテラルの解を元の変数に戻す　originはリスト
            if lit==None:
                continue
            for j in lit:
                ans=ans+' -'+str(return_table.get(j))
    return ans + ' ' + koteians


def weight_node(node): #タイルの最大数を求めるためのweight情報を計算する関数
    if node.weight!=None:
        return
    node.weight=0
    if node.type==NType.LIT:
        check_var = cor_table.get(node.lit)
        if check_var !=None:
            for i in check_var:
                if ('P1' in return_table.get(i)):
                    node.weight+=1
    elif node.type==NType.AND:
        for child in node.children:
            weight_node(node_list[child])
            node.weight+=node_list[child].weight
    elif node.type==NType.OR:
        weight_node(node_list[node.children[0]])
        weight_node(node_list[node.children[1]])
        node.weight=max(node_list[node.children[0]].weight,node_list[node.children[1]].weight)

def max_answer(node): #タイルが最大数の時の解を出す関数
    if node.type==NType.LIT:
        if node.lit>0:
            answer[abs(node.lit)]=True
        elif node.lit<0:
            answer[abs(node.lit)]=False
        #リテラルを返して解リストを更新
    elif node.type==NType.AND:
        #自分の子供を順に見ていく
        for child in node.children:
            max_answer(node_list[child])
    elif node.type==NType.OR:
        if node.weight==node_list[node.children[0]].weight:
            max_answer(node_list[node.children[0]])
        else:
            max_answer(node_list[node.children[1]])

max_node_list=[]
def count_max(node):
    global max_node_list
    if node.hasukai>0:
        return
    if node.type==NType.LIT:
        node.hasukai=1
        pass
    elif node.type==NType.AND:
        node.hasukai=1
        for child in node.children:
            count_max(node_list[child])
            node.hasukai*=node_list[child].hasukai
    elif node.type==NType.OR:
        if node_list[node.children[0]].weight==node_list[node.children[1]].weight:
            count_max(node_list[node.children[0]])
            count_max(node_list[node.children[1]])
            node.hasukai=node_list[node.children[0]].hasukai+node_list[node.children[1]].hasukai
            node.max_branch=None
            max_node_list.append(node.id)
        elif node_list[node.children[0]].weight>node_list[node.children[1]].weight:
            count_max(node_list[node.children[0]])
            node.hasukai=node_list[node.children[0]].hasukai
            node.max_branch=0
        else:
            count_max(node_list[node.children[1]])
            node.hasukai=node_list[node.children[1]].hasukai
            node.max_branch=1

def max_search(node): #ノードを辿っていく関数
    global max_stuck
    #print(node.id)
    if node.type==NType.LIT:
        if node.lit>0:
            answer[abs(node.lit)]=True
        elif node.lit<0:
            answer[abs(node.lit)]=False
        #リテラルを返して解リストを更新
    elif node.type==NType.AND:
        #自分の子供を順に見ていく
        for child in node.children:
            max_search(node_list[child])
    elif node.type==NType.OR:
        if node.max_branch == None:
            node.max_branch = 0
            max_stuck.append(node.id)
            max_search(node_list[node.children[0]])
        else:
            max_search(node_list[node.children[node.max_branch]])

max_stuck = []       ###[[id,LorR]]
max_started=False       ###関数next_answerで使用する変数
max_finish=False
max_answer_number=0
def max_next_answer(): #順に解を出力するための関数
    global max_started
    global max_stuck
    global max_finish
    global max_answer_number

    if max_finish==True:
        return
    if max_started==False:
        max_search(node_list[-1])
    else:
        while(len(max_stuck)>0 and node_list[max_stuck[-1]].max_branch==1):
            node_list[max_stuck[-1]].max_branch = None
            max_stuck.pop()
        if (len(max_stuck)>0):
            node_list[max_stuck[-1]].max_branch = 1
            max_search(node_list[-1])
            print(show_answer())
            max_answer_number += 1
        else:
            # print('no more answer')
            max_finish=True
    max_started=True

def max_howmany(node,number): #指定した番目の解を出力する関数
    if number>=node.hasukai:
        print('out of range')

    else:
        if node.type==NType.LIT:
            pass
        elif node.type==NType.OR:
            if number<node_list[node.children[0]].hasukai:
                node.max_branch=0
                max_stuck.append(node.id)
                max_howmany(node_list[node.children[0]],number)
            else:
                node.max_branch=1
                max_stuck.append(node.id)
                max_howmany(node_list[node.children[1]],number-node_list[node.children[0]].hasukai)
        elif node.type==NType.AND:
            c=node.hasukai
            N=number
            for child in node.children:
                c = c//node_list[child].hasukai
                q,N=divmod(N,c)
                max_howmany(node_list[child],q)


def odd_even(node):
    if node.odd_even!=None:
        return
    if node.type==NType.LIT:
        if node.weight%2==0:
            node.odd_even=True
        else:
            node.odd_even=False
    elif node.type==NType.AND:
        for child in node.children:
            odd_even(node_list[child])
        for child in node.children:
            if node.odd_even==None:
                node.odd_even=node_list[child].odd_even
            else:
                node.odd_even=node.odd_even^node_list[child].odd_even
    elif node.type==NType.OR:
        odd_even(node_list[node.children[0]])
        odd_even(node_list[node.children[1]])
        if node_list[node.children[0]].odd_even==True and node_list[node.children[1]].odd_even==True:
            node.odd_even=True
        elif node_list[node.children[0]].odd_even==False and node_list[node.children[1]].odd_even==False:
            node.odd_even=False
        else:
            return print('奇数もある')


def modelcount(node): #ノードが持つ解の数を計算する関数
    if node.count > 0:
        return node.count

    if node.type==NType.LIT:
        node.count = 1
    elif node.type==NType.OR:
        node.count = modelcount(node_list[node.children[0]])
        node.count += modelcount(node_list[node.children[1]])
    elif node.type==NType.AND:
        node.count = 1
        for child in node.children:
            node.count *= modelcount(node_list[child])
    else:
        print("Error: illegal node")

    return node.count

def howmany(node,number): #指定した番目の解を出力する関数
    if number>=node.count:
        print('out of range')

    else:
        if node.type==NType.LIT:
            pass
        elif node.type==NType.OR:
            if number<node_list[node.children[0]].count:
                node.branch=0
                or_stuck.append(node.id)
                howmany(node_list[node.children[0]],number)
            else:
                node.branch=1
                or_stuck.append(node.id)
                howmany(node_list[node.children[1]],number-node_list[node.children[0]].count)
        elif node.type==NType.AND:
            c=node.count
            N=number
            for child in node.children:
                c = c//node_list[child].count
                q,N=divmod(N,c)
                howmany(node_list[child],q)
#        search(node_list[-1])


atom  = re.compile(r'[a-zA-Z]+([0-9]*)\(([0-9,]+)\)')

def draw(tiles, utfMode, listMode):
    if(listMode):
        for t in tiles:
            print('{}'.format(t))
    else:
        rev.draw_tiles(tiles, utfMode)

def draw_answer(size): #解を描画する関数
    M = size*3   # J型領域の幅
    tiles = set()
    for i in range(1,len(answer)):
        if answer[i]==True:
            lit = cor_table.get(i)#正リテラルの解を元の変数に戻す　originはリスト
            if lit==None:
                continue
            for j in lit:
                tile_str = str(return_table.get(j))
                (t, poss) = (atom.match(tile_str).group(1), atom.match(tile_str).group(2))
                if t == '':
                    type = 0
                else:
                    type = int(t)
                tile = rev.strToTileM(poss, M, type)
                tiles.add(tile)

        elif answer[i]==False:
            nolit = cor_table.get(-i)
            if nolit==None:
                continue
            for j in nolit:
                tile_str = str(return_table.get(j))
                (t, poss) = (atom.match(tile_str).group(1), atom.match(tile_str).group(2))
                if t == '':
                    type = 0
                else:
                    type = int(t)
                tile = rev.strToTileM(poss, M, type)
                tiles.add(tile)

    if (tiles != set()):
        draw(tiles, True, False)#ファイルに書き込むときは第二引数をFalseにしたほうが綺麗になる


"""
def weight_proof_node(node): #タイルの最大数を求めるためのweight情報を計算する関数
    #if node.weight_list!=None:
    #    return
    node.weight_list=[]
    if node.type==NType.LIT:
        node.weight_list.append(node.weight)
    elif node.type==NType.AND:
        weightlist=[]
        for child in node.children:
            weight_proof_node(node_list[child])
            weightlist.append(node_list[child].weight_list)
        for i in range(len(weightlist)-1):
            weightlist[0]=plus(weightlist[0],weightlist[1])
            weightlist.pop(1)
        node.weight_list=weightlist[0]

    elif node.type==NType.OR:
        weight_proof_node(node_list[node.children[0]])
        weight_proof_node(node_list[node.children[1]])
        list_a=node_list[node.children[0]].weight_list+node_list[node.children[1]].weight_list
        node.weight_list=list(set(list_a))

def plus(list1,list2=[]):
  list_a=[]
  for i in list1:
    for j in list2:
      list_a.append(i+j)
  return list(set(list_a))
"""
###########################################################################################
###############################ファイル読み込み処理###########################################
###########################################################################################

nnf_start = time.time()

with open(nnfout_filename) as f:
    print('d-DNNFファイル読み込み中...')
    for line in f:
       line_block = line.split()
       if (line_block[0]=='v'):
           key = int(line_block[2])
           value = int(line_block[1])
           if key in cor_table:
               cor_table.get(key).append(value)
           else:
               cor_table[key] = [value]
       elif (line_block[0]=='p'):
           litcount=int(line_block[3])
       elif (line_block[0]=='a'):
           a = list(map(int,a[1:-1]))
       elif (line_block[0]=='L'):
           node_list.append(Node(NType.LIT,lit=int(line_block[1])))
       elif (line_block[0]=='A'):
           node_list.append(Node(NType.AND,lits=list(map(int,line_block[2:]))))
       elif (line_block[0]=='O'):
           node_list.append(Node(NType.OR,lits=list(map(int,line_block[3:]))))

for i in range(litcount+1):
    answer.append(None)

nnf_end = time.time()
print('nnf parse time:', nnf_end-nnf_start, 's')

cnf_start = time.time()

with open(cnf_filename) as f:
    print('PB変数とCNFファイルの対応情報を読み込み中...')
    for line in f:
        lineblock = line.split()
        if lineblock!=[]:
            if (lineblock[0]=='cv'):
                lineblock.pop(0)
                for i in lineblock:
                    var_block=i.split(':')
                    return_table[int(var_block[0])]=var_block[1]

cnf_end = time.time()
print('cnf parse time', cnf_end-cnf_start, 's')

###########################################################################################
###############################ファイル読み込み処理終了########################################
###########################################################################################


###########################################################################################
#######################################メイン処理###########################################
###########################################################################################

while True:
    drawsize=input('問題のサイズはいくつですか\n')
    if drawsize.isdecimal():
        drawsize=int(drawsize)
        break
    else:
        print('整数を入力してください')

mainstart=True
two_start=False
three_start=False
five_start=False
answer_number=0

while (mainstart==True) :
    main=input('1 一つずつ解を出す \n2 指定した順目の解を出す \n3 斜交いタイルの最大数を求める \n4 1つずつ解を出す（斜交い） \n5 指定した順目の解を出す（斜交い）\n6 サイズの変更 \n7 終了 \n')
    if main=='1':
        reset=input('スタックとノードを初期化しますか \n 0 (はい) \n 0以外のキーを入力 (いいえ)')
        if reset=='0':
            reset_conf=input('本当に初期化しますか？ \n 0 (はい) \n 0以外のキーを入力 (いいえ)')
            if reset_conf=='0':
                finish=False
                started=False
                answer_number=0
                or_stuck = []
                for node in node_list:
                    if node.type==NType.OR:
                        node.branch = None
            else:
                pass
        else:
            pass

        while True:
            next_answer()
            if finish:
                print('no more answer\n')
                break
            draw_answer(drawsize)
            print('これは'+str(answer_number)+'番目の解です')
            one_end=input('辞める場合は 0 を入力してください\n続ける場合はキーを入力してください\n')
            if one_end=='0':
                break

    elif main=='2':
        if two_start==False:
            print('モデル計数中...')
            mc_start = time.time()
            modelcount(node_list[-1])    ###各ノードに解の個数を情報として持たせる
            mc_end = time.time()
            print('model count time:', mc_end - mc_start, 's')
            two_start=True
        while True:
            or_stuck = []
            for node in node_list:
                if node.type=='OR':
                    node.branch = None
            print('解は 0 から '+str(node_list[-1].count-1)+' までです')
            num=input('求めたいのは何番目の解ですか？\n')
            howmany(node_list[-1],int(num))
            search(node_list[-1])
            draw_answer(drawsize)
            started=True
            answer_number = int(num)
            two_end=input('辞める場合は 0 を入力してください\n続ける場合はキーを入力してください\n')
            if two_end=='0':
                break
    elif main=='3':
        if three_start==False:
            print('斜交いタイルの最大数を計算中...')
            mnoc_start = time.time()
            weight_node(node_list[-1])    ###各ノードに情報を持たせる
            three_start=True
            max_answer(node_list[-1])
            print('斜交いタイルの最大数を計算')
            count_max(node_list[-1])
            #odd_even(node_list[-1])  斜交いタイルが偶数個である証明
            mnoc_end = time.time()
            print('max#oc time:', mnoc_end - mnoc_start, 's')
        draw_answer(drawsize)
        print('斜交いタイルの最大数は'+str(node_list[-1].weight)+'です')
        print('斜交いタイルの最大数の解の数は'+str(node_list[-1].hasukai)+'です')
        #print(node_list[-1].odd_even) 斜交いタイルが偶数個である証明
    if main=='4':
        max_reset=input('スタックとノードを初期化しますか \n 0 (はい) \n 0以外のキーを入力 (いいえ)')
        if max_reset=='0':
            max_reset_conf=input('本当に初期化しますか？ \n 0 (はい) \n 0以外のキーを入力 (いいえ)')
            if max_reset_conf=='0':
                max_finish=False
                max_started=False
                max_answer_number=0
                max_stuck = []
                if node_list[-1].weight==None:
                    weight_node(node_list[-1])
                if node_list[-1].hasukai==0:
                    count_max(node_list[-1])
                for node in max_node_list:
                    node_list[node].max_branch = None
            else:
                pass
        else:
            pass

        while True:
            max_next_answer()
            if max_finish:
                print('no more answer\n')
                break
            draw_answer(drawsize)
            print('これは'+str(max_answer_number)+'番目の解です')
            four_end=input('辞める場合は 0 を入力してください\n続ける場合はキーを入力してください\n')
            if four_end=='0':
                break
    elif main=='5':
        if five_start==False:
            print('モデル計数中...')
            max_mc_start = time.time()
            weight_node(node_list[-1])
            count_max(node_list[-1])    ###各ノードに解の個数を情報として持たせる
            max_mc_end = time.time()
            print('model count time:', max_mc_end - max_mc_start, 's')
            five_start=True
        while True:
            max_stuck = []
            for node in max_node_list:
                node_list[node].max_branch = None
            print('解は 0 から '+str(node_list[-1].hasukai-1)+' までです')
            max_num=input('求めたいのは何番目の解ですか？\n')
            max_howmany(node_list[-1],int(max_num))
            max_search(node_list[-1])
            draw_answer(drawsize)
            max_started=True
            max_answer_number = int(max_num)
            five_end=input('辞める場合は 0 を入力してください\n続ける場合はキーを入力してください\n')
            if five_end=='0':
                break
    elif main=='6':
        while True:
            drawsize=input('問題のサイズはいくつですか\n')
            if drawsize.isdecimal():
                drawsize=int(drawsize)
                break
            else:
                print('整数を入力してください')
    elif main=='7':
        print('終了します\n')
        mainstart=False
    else:
        print('error\n')
