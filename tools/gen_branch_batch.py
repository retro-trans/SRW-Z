# -*- coding: utf-8 -*-
"""Generate the small branch records (Garrod flower scene + Gainer bazaar scene)
by matching on the exact JP source string, so index-offset variants all resolve."""
import json
WORK = r'E:\Projects\SRW Z\_work'


def bl(x):
    return len(x.encode('cp932'))


M = {
"ロラン\n「ガロード…その化粧品のセット、\n　売ってしまうのかい？」": 'Loran\n"Garrod.. that cosmetics\nset, you\'re selling it?"',
"ガロード\n「まあな…」": 'Garrod\n"Yeah, well.."',
"ソシエ\n「それ…ティファにプレゼントするために\n　買ったんじゃない…！」": 'Sochie\n"You bought that as\na gift for Tiffa,\ndidn\'t you..!"',
"ソシエ\n「まさか、あんた…！\n　ティファの事、諦めたの！？」": 'Sochie\n"Don\'t tell me..!\nHave you given up\non Tiffa!?"',
"ガロード\n「勘違いするなよ。\n　こいつを売って、ティファを迎えにいく時の\n　プレゼントの資金の足しにするんだよ」": 'Garrod\n"Don\'t get me wrong.\nI\'ll sell it to help fund\na gift for when I go\nbring Tiffa home."',
"ロラン\n「結局、その化粧品もあげてなかったんだ…」": 'Loran\n"So in the end you never\ngave her those\ncosmetics.."',
"ガロード\n「こいつはティファには\n　まだ早かったみたいなんだ」": 'Garrod\n"Seems this stuff was\nstill too grown-up\nfor Tiffa."',
"ガロード\n「だから、今すぐに喜んでもらえそうなものに\n　変えようと思ってよ」": 'Garrod\n"So I figured I\'d swap it\nfor something she\'d\nlove right now."',
"レントン\n「さっすが、ガロード！\n　どんな時にもポジティブだ！」": 'Renton\n"That\'s Garrod for you!\nPositive no matter what!"',
"ガロード\n「落ち込んでいてもティファが\n　戻ってくるわけじゃない…」": 'Garrod\n"Moping won\'t bring\nTiffa back to me.."',
"ガロード\n「だったら、気持ちだけでも前向きに\n　ティファの事を考えるぜ」": 'Garrod\n"So I\'ll stay upbeat,\nat least in spirit,\nand think of Tiffa."',
"カリス\n「君らしい考え方だよ、ガロード」": 'Caris\n"That\'s just like you,\nGarrod."',
"エニル\n「そういう事なら、\n　あたしがプレゼントを選ぶのを\n　手伝ってあげてもいいわよ」": 'Ennil\n"In that case, I could\nhelp you pick out\nthe gift, if you like."',
"ガロード\n「本当か、エニル？」": 'Garrod\n"Really, Ennil?"',
"エニル\n「ちょっと悔しいけど\n　あなたの笑顔が見られるんなら\n　手を貸してあげる気にもなるわ」": 'Ennil\n"It stings a bit, but if\nit means seeing you\nsmile, I\'ll help out."',
"ガロード\n「ありがとよ！\n　じゃあ、早速、マーケットに\n　付き合ってもらうぜ！」": 'Garrod\n"Thanks! Then come\nwith me to the market\nright now!"',
"ガロード\n「ありがとよ！\n　じゃあ、早速マーケットに\n　付き合ってもらうぜ！」": 'Garrod\n"Thanks! Then come\nwith me to the market\nright now!"',
"キッド\n「それで買ったのが、この花束か」": 'Kid\n"And so you bought\nthis bouquet."',
"パーラ\n「ステキじゃん！\n　女の子はやっぱり綺麗な物が好きだし、\n　きっとティファ、喜ぶと思うな！」": 'Pala\n"How lovely! Girls do\nlove pretty things -\nTiffa\'s sure to be\nthrilled!"',
"キッド\n「でもよ…ティファに会う前に\n　この花、枯れちゃうんじゃねえの？」": 'Kid\n"But hey.. won\'t these\nflowers wilt before\nyou meet Tiffa?"',
"エニル\n「その心配は要らないわ。\n　これはプリザーブドフラワーにするために\n　買ったんだから」": 'Ennil\n"No need to worry.\nI bought them to make\npreserved flowers."',
"パーラ\n「何それ…？」": 'Pala\n"What\'s that..?"',
"ガロード\n「花を保存する方法なんだってよ。\n　これでティファに会う時にも\n　綺麗に咲いたまんまってわけだ」": 'Garrod\n"It\'s a way to preserve\nflowers. So they\'ll still\nbe in bloom when I\nmeet Tiffa."',
"キッド\n「で、言うんだろ？\n　ボクの想いも、この花の美しさのように\n　永遠です、なんてよ！」": 'Kid\n"And then you\'ll say it,\nright? \'My love, like this\nbloom, is eternal!\'"',
"ガロード\n「ば、馬鹿！\n　そんな恥ずかしい事、言えるかよ！」": 'Garrod\n"Y-you idiot! Like I\'d\nsay something that\nembarrassing!"',
"ゲイナー\n（あの様子…）": 'Gainer\n(That look..)',
"ロラン\n（もしかして、ガロード…）": 'Loran\n(Could it be, Garrod..)',
"レントン\n（本気で言う気だったんじゃ…）": 'Renton\n(He really meant\nto say it..)',
"パーラ\n（あ〜あ…）": 'Pala\n(Aw, man..)',
"エニル\n（ちょっとヤケちゃうかな…）": 'Ennil\n(Maybe I\'m a bit\njealous..)',
"ガロード\n（待ってろよ、ティファ…。\n　この花を持って…俺、絶対にティファの事、\n　迎えに行くからな…）": 'Garrod\n(Wait for me, Tiffa..\nI\'ll bring these flowers\nand come to fetch you,\nno matter what..)',
# --- Gainer bazaar scene (rec163/164) ---
"レントン\n（エウレカとホランドとヴォダラク…。\n　俺の知らない何かが、そこにはある…）": 'Renton\n(Eureka, Holland, the\nVodarac.. There\'s\nsomething there I\ndon\'t know about..)',
"ゲイナー\n「どうかしたのかい、レントン？」": 'Gainer\n"Something wrong,\nRenton?"',
"レントン\n「い、いや…何でもないです！」": 'Renton\n"N-no.. it\'s nothing!"',
"レントン\n「せっかく、ゲイナー兄さんが\n　バザーに誘ってくれたってのに\n　ボーっとしててすみません」": 'Renton\n"You invited me to the\nbazaar and here I am\nspacing out. Sorry."',
"ムーンドギー\n「で、ゲイナー…\n　おめ、なして俺達を誘ったんだ？」": 'Moondoggie\n"So, Gainer.. why\'d\nyou invite us along\nanyway?"',
"ゲイナー\n「うん…もう不要になったんで\n　これを売ろうと思ったんだけど…」": 'Gainer\n"Well.. I don\'t need\nthis anymore, so I\nthought I\'d sell it.."',
"レントン\n「これって！？」": 'Renton\n"This is..!?"',
"ギジェット\n「これ、『ｒａｙ＝ｏｕｔ』の創刊号じゃない！\n　かなりのレア物よ！」": 'Gidget\n"That\'s the debut issue\nof \'ray=out\'! Quite\nthe rare find!"',
"ゲイナー\n「やっぱり、値打ちものなんだ。\n　君達に見てもらって、よかったよ」": 'Gainer\n"So it is valuable.\nGlad I showed it\nto you all."',
"レントン\n「ゲイナー兄さん、\n　これ、売っちゃうんですか？」": 'Renton\n"Gainer, are you\nreally going to\nsell it?"',
"ゲイナー\n「この本を買った時の目的は果たしたからね。\n　その代わり…」": 'Gainer\n"It served the purpose\nI bought it for.\nInstead.."',
"ギジェット\n「わかった…！\n　サラに何かプレゼント、買うんでしょ！」": 'Gidget\n"I get it..! You\'re buying\na gift for Sara,\naren\'t you!"',
"ゲイナー\n「そ、そういうわけじゃないけど…\n　せっかくだから、後で価値が出そうな\n　お宝と交換しようかなって思って…」": 'Gainer\n"Th-that\'s not it..\nI just thought I\'d\ntrade it for pricier\ntreasure later.."',
"ギジェット\n「ＯＫ、任せといて！\n　あたし達がプレゼント、探してあげるよ」": 'Gidget\n"OK, leave it to us!\nWe\'ll help you find\na gift."',
"ゲイナー\n「だから…！\n　そうじゃないんだってば！」": 'Gainer\n"I told you..!\nThat\'s not what\nthis is!"',
"ゲイナー\n「あ、あのサラ…\n　よかったら、このディスク…聴かない？」": 'Gainer\n"U-um, Sara.. if you\nlike, want to listen\nto this disc?"',
"サラ\n「ラクス・クライン…？\n　あのプラントで人気の歌手？」": 'Sara\n"Lacus Clyne..? That\nsinger who\'s popular\nin the PLANTs?"',
"ヴィーノ\n「マジかよ！\n　このディスク、サイン入りだぜ！」": 'Vino\n"No way! This disc\nis autographed!"',
"ヨウラン\n「お前…よくこんなレアアイテム、\n　ゲット出来たな」": 'Yolant\n"You.. how\'d you get\nyour hands on such\na rare item?"',
"ゲイナー\n「ま、まあね」": 'Gainer\n"W-well, you know."',
"ゲイナー\n（ありがとう、ギジェット…）": 'Gainer\n(Thank you, Gidget..)',
"サラ\n「でも、興味無い。\n　ＵＮで見たけどラクス・クラインって、\n　お色気路線で好きじゃないから」": 'Sara\n"Not interested. Saw\nher on the UN net -\nLacus Clyne\'s too\nsexy for me."',
"ゲイナー\n「え…」": 'Gainer\n"Huh.."',
"サラ\n「それよりゲイナーも手伝ってよ。\n　ミネルバの資材でヤーパンの天井の\n　補修をするんだから」": 'Sara\n"Anyway, help out too,\nGainer. We\'re fixing\nYapan\'s ceiling with\nMinerva\'s materials."',
"ゲイナー\n（せっかくのレアものなのに不発…。\n　ツイてないな…）": 'Gainer\n(A rare find, and it\nflopped.. Just not\nmy day..)',
"サラ\n「ガウリ隊長とベローも待ってるよ。\n　頑張ろうね、ゲイナー」": 'Sara\n"Captain Gauli and\nBello are waiting too.\nLet\'s do our best,\nGainer."',
"ゲイナー\n「うん」": 'Gainer\n"Yeah."',
"ヨウラン\n「…プレゼントは不発だったけど\n　いい雰囲気じゃん」": 'Yolant\n"..Gift flopped, but\nthe mood between them\nain\'t bad."',
"ヴィーノ\n「しかし、今のラクス・クライン…\n　人気ないのかな？」": 'Vino\n"Still, Lacus Clyne\nthese days.. is she\nnot popular?"',
"ヨウラン\n「大幅にイメチェンしたせいかもな。\n　…でも、俺は嫌いじゃないぜ」": 'Yolant\n"Maybe \'cause she\nrevamped her image.\n..But I don\'t mind it."',
"ヴィーノ\n「俺も、俺も！\n　何かプロポーションも大幅に\n　パワーアップしてるし！」": 'Vino\n"Me too, me too!\nHer figure got a\nbig power-up too!"',
"ヨウラン\n「一般受けはともかく\n　プラントでの人気は相変わらずらしいな」": 'Yolant\n"Public aside, she\'s\nstill as popular as\never in the PLANTs."',
"ヴィーノ\n「あ〜あ…もう雪も飽きてきたから\n　ラクス・クラインのコンサートで\n　盛り上がりたいぜ…」": 'Vino\n"Man.. I\'m sick of the\nsnow. I wanna get\nhyped at a Lacus\nClyne concert.."',
}

targets = [163, 164, 169, 170, 175, 176]
for n in targets:
    try:
        rows = json.load(open(WORK + r'\analysis\rec%03d_work.json' % n, encoding='utf-8'))
    except FileNotFoundError:
        print("rec%03d: no work.json" % n)
        continue
    T = {}
    miss = []
    over = []
    for r in rows:
        jp = r['jp']
        i = r['i']
        if jp in M:
            en = M[jp]
            if bl(en) > r['budget']:
                over.append((i, bl(en), r['budget']))
            T[i] = en
        else:
            miss.append((i, r['budget'], r['jp']))
    if miss:
        print("rec%03d MISSING %d rows:" % (n, len(miss)))
        for i, b, jp in miss[:8]:
            print("   i=%d (b%d): %r" % (i, b, jp[:60]))
        continue
    if over:
        print("rec%03d OVER: %s" % (n, over))
        continue
    lines = ["# -*- coding: utf-8 -*-", '"""Stage record %d dialogue."""' % n, "", "T = {"]
    for k in sorted(T):
        lines.append("    %d: %r," % (k, T[k]))
    lines.append("}")
    open("rec%03d_en.py" % n, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("rec%03d: %d rows written, 0 over" % (n, len(T)))
