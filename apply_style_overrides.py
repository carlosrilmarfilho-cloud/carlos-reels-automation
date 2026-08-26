from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VIRAL_COPY = ROOT / "viral_copy.json"
PROFILES = ROOT / "video_profiles.json"
RENDER = ROOT / "render.py"

AUTHORIAL = {
    "forro_antigo": {
        "overlays": [
            "Terapia do dia: um forró velho e nenhum conselho.",
            "Meu humor melhora uns 70% quando entra uma sanfona dessas.",
            "Ser nordestino é reconhecer essa terapia em três segundos.",
            "Isso aqui não é nostalgia. É manutenção preventiva do juízo.",
            "Tem dia que eu não quero conversar. Quero esse forró no talo.",
            "Se tocar isso no carro, eu erro a saída e sigo cantando.",
            "A certidão pode dizer 1995. O ouvido claramente é mais antigo.",
            "Eu não superei essa época e, sinceramente, nem pretendo.",
            "Nordestino longe de casa escuta isso com outro peso.",
            "Três segundos de sanfona e pronto: já melhorei da semana.",
            "Tem música que envelhece. Isso aqui só fica mais gostoso.",
            "A terapia de hoje veio com zabumba, sanfona e lembrança.",
            "Se você sabe cantar essa, nós já temos assunto pra uma noite.",
            "Isso aqui explica por que nordestino não precisa de silêncio pra relaxar.",
            "O problema continua, mas agora eu tô cantando por cima dele.",
            "Forró antigo: porque sofrer parado é falta de criatividade.",
            "Uma dessas e eu volto pro Nordeste sem comprar passagem.",
            "Eu só queria ouvir uma música. Ganhei quinze lembranças de brinde.",
            "Quem foi criado ouvindo isso não aceita qualquer refrão hoje em dia.",
            "Se isso não for patrimônio emocional do Nordeste, eu não sei o que é.",
            "Meu tipo de autocuidado tem triângulo, zabumba e volume alto.",
            "Isso aqui devia ser recomendado pra dia ruim e saudade acumulada.",
            "Forró bom não pede licença. Entra e reorganiza o ambiente.",
            "A música nem terminou e eu já tô melhor do que comecei.",
        ],
        "captions": [
            "Hoje a sessão foi essa. Quem tiver um forró melhor, deixa o nome que eu avalio a receita. 🪗",
            "Nordestino entende: às vezes a saudade não quer conversa, quer volume. Qual clássico te leva pra casa?",
            "Eu apertei o play só pra ouvir. Quando vi, já tava lembrando de gente, lugar e fase da vida.",
            "Forró antigo tem esse defeito: você começa ouvindo e termina contando história. Qual música faz isso contigo?",
            "Se você cantou antes de chegar no refrão, pode ficar tranquilo: aqui é lugar de gente experiente. 😂",
            "Tem dia que a cabeça pede silêncio. A minha, claramente, pediu sanfona. Qual é tua terapia de hoje?",
            "Essa é daquelas que não precisa de trend nem efeito. Bota pra tocar e deixa a memória fazer o resto.",
            "Quem mora longe do Nordeste sabe o que uma sanfona dessas consegue fazer em poucos segundos.",
            "Não é sobre viver no passado. É sobre lembrar de onde veio sem pedir desculpa por gostar do que é bom.",
            "O algoritmo pode gostar de novidade. Meu ouvido continua respeitando os clássicos. Qual não pode faltar?",
            "Tem música que eu salvo na playlist. Tem outras que eu salvo porque parecem um pedaço de casa.",
            "Se essa batida te arrancou um sorriso antes da letra, já cumpriu a missão de hoje."
        ],
    },
    "brega": {
        "overlays": [
            "Terapia do dia: sofrer bonito e com uma música boa.",
            "Tem recaída que não manda mensagem. Ela toca no refrão.",
            "Eu tava bem até a música lembrar por mim.",
            "Brega bom é isso: você ri e sofre na mesma estrofe.",
            "Se veio alguém na cabeça, não fui eu. Foi a música.",
            "O problema do brega é que ele conhece detalhes demais.",
            "Eu já tinha superado. A playlist aparentemente não.",
            "Não resolve a vida, mas dá uma trilha sonora decente pro caos.",
            "Tem coisa que terapia nenhuma escuta porque só o brega sabe contar.",
            "Essa letra leu a conversa que você jurou que tinha apagado.",
            "O coração tava quieto. Aí entrou esse refrão sem autorização.",
            "Quem nunca sofreu cantando alto ainda não entendeu o brega.",
            "Brega é a arte de transformar vergonha alheia em memória afetiva.",
            "Se doeu, canta mais alto que fica pelo menos cinematográfico.",
            "O volume sobe e a dignidade emocional tira cinco minutos de folga.",
            "A música é antiga. O problema emocional continua atualíssimo.",
            "Isso aqui pega a saudade, bota microfone e manda ela trabalhar.",
            "Eu queria paz. O brega me ofereceu um refrão e lembranças.",
            "Tem música que ajuda a esquecer. Essa claramente veio fazer o contrário.",
            "A vantagem do brega é sofrer sem perder a melodia.",
        ],
        "captions": [
            "Brega bom não pergunta se você superou. Ele toca e deixa você se explicar sozinho. 😂",
            "Se alguém apareceu na tua cabeça, deixa o nome em paz. Só comenta a música.",
            "Essa é daquelas que fazem a pessoa olhar pro nada como se tivesse num clipe. Quem conhece?",
            "O problema não sumiu, mas agora pelo menos tem trilha sonora. Qual brega entra na sequência?",
            "Tem refrão que chega com mais informação do que deveria. Essa acertou ou passou longe?",
            "Eu gosto de música que diverte. Mas confesso que as que complicam o emocional têm seu valor.",
            "Quem viveu uma história ouvindo brega nunca escuta só a melodia. Escuta tudo de novo.",
            "Se é pra sofrer, que seja com arranjo bom e refrão decorado. Me dá o próximo clássico.",
            "Brega é terapia coletiva: todo mundo finge que tá cantando só pela música. 😂",
            "Essa música não mandou mensagem pra ninguém, mas tenho certeza que deu vontade em muita gente.",
            "Qual é aquela que você promete não ouvir e sempre volta quando bate saudade?",
            "Eu só apertei o play. A responsabilidade pelas lembranças é inteiramente do compositor."
        ],
    },
    "romantica": {
        "overlays": [
            "Tem letra romântica que fala o que a gente não teve coragem.",
            "Eu gosto de música que dá vontade de mandar pra uma pessoa só.",
            "O amor é bonito até a playlist começar a dar detalhes.",
            "Tem refrão que parece indireta mesmo quando ninguém pediu.",
            "Essa é pra quem diz que superou e ainda sabe cada palavra.",
            "Às vezes a saudade escolhe uma música antes de escolher um nome.",
            "Tem gente que volta pela mensagem. Outras voltam pelo refrão.",
            "Essa música sabe exatamente onde a conversa ficou pela metade.",
            "Quem ama direito escuta certas letras com um pouco mais de cuidado.",
            "Eu não mandei mensagem. Mas confesso que a música quase mandou por mim.",
            "Tem canção que não lembra alguém. Lembra uma versão nossa.",
            "A letra é romântica. O histórico de quem ouve é que complica tudo.",
            "Essa música é boa demais pra dedicar pra pessoa errada.",
            "Tem saudade que não pede volta. Só pede uma música dessas.",
            "Se você pensou numa pessoa específica, a letra fez o trabalho dela.",
            "O perigoso da música romântica é ela ter memória melhor que a nossa.",
            "Tem coisa que não precisa de textão. Um refrão desses já entrega.",
            "Eu gosto quando a música diz bonito aquilo que na vida saiu confuso.",
            "O amor passa por fases. Algumas ficam guardadas na playlist.",
            "Essa aqui é pra ouvir sem pressa e sem abrir conversa antiga.",
        ],
        "captions": [
            "Tem música que a gente manda pra alguém. E tem música que é melhor só ouvir e ficar quieto. Essa é qual?",
            "Se uma pessoa veio na tua cabeça antes do refrão, a música já respondeu por você.",
            "Música romântica boa não precisa exagerar. Ela só encontra uma lembrança e pronto.",
            "Qual canção você não consegue ouvir sem associar a alguém? Não precisa marcar a pessoa. 😂",
            "Essa letra tem cara de mensagem que a gente escreve, apaga e resolve deixar na música.",
            "Tem histórias que acabam e ainda assim continuam com uma trilha sonora muito boa.",
            "Eu gosto dessas que parecem simples até você prestar atenção na letra. Aí complicou.",
            "O coração pode até seguir em frente. A playlist às vezes demora um pouco mais.",
            "Se você dedicaria essa pra alguém, já sabe: manda o vídeo e não explica nada.",
            "Nem toda saudade pede reencontro. Algumas só pedem três minutos de música.",
            "Essa foi escrita pra alguém específico ou todo mundo já viveu algo parecido?",
            "Tem frase que na conversa parece demais. Na música, encaixa exatamente."
        ],
    },
    "saudade": {
        "overlays": [
            "Saudade tem dessas: escolhe uma música e aparece sem avisar.",
            "Morar longe ensina que algumas músicas também são passagem de volta.",
            "Tem dia que o corpo tá na Europa e a cabeça claramente não.",
            "Uma música dessas e a distância fica uns quilômetros mais curta.",
            "Quem mora fora sabe: tem refrão que parece cheiro de casa.",
            "Saudade não respeita fuso horário, muito menos playlist.",
            "Eu saí de casa. Tem música que ainda não deixou a casa sair de mim.",
            "Tem som que faz uma cidade inteira aparecer na cabeça.",
            "Às vezes voltar pra casa dura exatamente o tempo de uma música.",
            "A distância pesa menos quando a memória encontra uma trilha boa.",
            "Tem coisa do Brasil que cabe inteira dentro de um refrão.",
            "Quem foi embora entende por que certas músicas doem bonito.",
            "A saudade tava quieta. Aí essa música resolveu trabalhar.",
            "Eu não tava lembrando de casa. A música tava.",
            "Tem dia que um sotaque numa canção vale mais que qualquer chamada de vídeo.",
            "A gente muda de país, mas algumas músicas continuam sabendo nosso endereço.",
            "Tem refrão que não toca no ouvido. Toca numa rua que ficou longe.",
            "Morar fora é aprender que até música pode dar vontade de voltar.",
            "A saudade não precisa de motivo. Às vezes precisa só de três acordes.",
            "Se isso te levou pra casa por alguns segundos, já valeu o play.",
        ],
        "captions": [
            "Quem mora fora sabe que saudade às vezes chega por um cheiro, uma comida ou uma música. Hoje veio por aqui.",
            "Essa me levou pra longe sem eu sair do lugar. Qual música sempre te leva de volta pra casa?",
            "Tem dia que a distância parece normal. Aí toca um negócio desses e muda tudo.",
            "O passaporte muda o endereço; algumas músicas fazem questão de lembrar a origem.",
            "Se você mora fora, comenta a primeira música brasileira que te dá vontade de voltar.",
            "Tem refrão que encurta oceano melhor do que chamada de vídeo. Essa fez isso contigo?",
            "Eu gosto de morar fora, mas certas músicas deixam bem claro que uma parte da gente nunca fez a mudança.",
            "A saudade não precisa ser triste. Às vezes ela só senta do lado e canta junto.",
            "Qual som tem cheiro de casa pra você? Essa pergunta sempre rende histórias boas.",
            "Tem música que lembra uma pessoa. Essa me lembra lugar, rua, clima e fase da vida inteira.",
            "Morar longe também é descobrir quantas coisas pequenas viram gigantes quando fazem falta.",
            "Se essa te levou pra algum lugar específico, comenta só a cidade. O resto a gente entende."
        ],
    },
    "musica_terapia": {
        "overlays": [
            "Terapia do dia: ouvir isso até a cabeça parar de discutir comigo.",
            "Hoje eu não precisava de conselho. Precisava exatamente dessa música.",
            "Três minutos disso e eu volto a ser uma pessoa minimamente sociável.",
            "Minha terapia de hoje tem refrão. Amanhã a gente vê o resto.",
            "Não resolveu minha vida. Mas melhorou bastante os próximos minutos.",
            "Tem dia que pensar menos e ouvir mais é uma ótima estratégia.",
            "A cabeça tava barulhenta. A música ganhou no volume e no argumento.",
            "Meu autocuidado de hoje foi apertar o play e não explicar nada pra ninguém.",
            "Essa música não dá conselho. Talvez por isso ajude mais.",
            "Se o dia tá uma bagunça, começa pelo que cabe em três minutos.",
            "Tem terapia que começa com 'me conta'. A minha hoje começou com play.",
            "Eu não tava procurando resposta. Só uma música que entendesse a pergunta.",
            "Às vezes o melhor que eu faço por mim é aumentar o volume.",
            "A vida não ficou fácil. Eu só fiquei uns três minutos mais leve.",
            "Tem dia que a pausa que faltava vem em forma de música.",
            "Não é fugir do problema. É só dar um intervalo decente pra cabeça.",
            "Minha mente abriu vinte abas. Essa música conseguiu fechar umas cinco.",
            "Hoje a terapia foi cantar até o pensamento perder a vez.",
            "Tem música que não cura nada. Mas segura a gente no lugar certo por um tempo.",
            "Se você precisava desacelerar, deixa essa terminar antes de seguir.",
            "O mundo pode esperar três minutos. Essa parte aqui merece.",
            "Meu tipo de meditação claramente vem com bateria, voz e refrão.",
            "A sessão de hoje foi curta: play, volume alto e cabeça mais leve.",
            "Tem dia que a gente não precisa entender tudo. Só precisa de uma música boa.",
        ],
        "captions": [
            "Terapia do dia concluída com sucesso: três minutos sem tentar resolver a vida inteira de uma vez.",
            "Tem música que não dá resposta, mas coloca a cabeça num lugar melhor pra pensar. Essa fez isso comigo.",
            "Hoje eu escolhi não discutir com o dia. Botei uma música e deixei ele passar um pouco.",
            "Se teu cérebro também abriu cinquenta abas hoje, escolhe uma música e fecha pelo menos algumas. 😂",
            "A vida continua igual depois do refrão. A diferença é que a gente pode continuar um pouco melhor.",
            "Qual música você usa quando não tá com vontade de ouvir conselho de ninguém?",
            "Nem tudo precisa virar reflexão profunda. Às vezes uma música boa já cumpre o expediente.",
            "Eu gosto de chamar isso de terapia do dia porque funciona rápido e ainda dá pra cantar junto.",
            "Tem som que organiza o humor sem explicar absolutamente nada. Essa entra na tua lista?",
            "Se isso te fez ficar alguns segundos sem pensar no resto, já teve utilidade.",
            "Minha recomendação de hoje é simples: deixa a música acabar antes de voltar pro problema.",
            "Qual foi tua terapia musical de hoje? Quero roubar umas recomendações pros próximos vídeos."
        ],
    },
    "nordeste_identidade": {
        "overlays": [
            "Ser nordestino é carregar casa até quando o endereço muda.",
            "O sotaque vai na mala mesmo quando a passagem é só de ida.",
            "Eu posso morar longe. Meu ouvido continua com CEP no Nordeste.",
            "Nordestino não perde a raiz. No máximo muda o fuso horário.",
            "Tem orgulho que aparece antes mesmo de alguém perguntar de onde você é.",
            "O mundo é grande, mas meu senso de casa continua apontando pro Nordeste.",
            "Ser nordestino é reconhecer um pedaço de casa no primeiro acorde.",
            "A distância só serviu pra eu gostar ainda mais de onde eu vim.",
            "Meu endereço mudou. Meu sotaque não recebeu o memorando.",
            "Tem gente que leva lembrança na mala. Nordestino leva cultura inteira.",
            "Eu moro fora, mas certas músicas entregam minha origem em segundos.",
            "Nordeste não é tema de vídeo. É o jeito que muita coisa faz sentido pra mim.",
            "O sotaque pode chamar atenção. Pra mim ele só chama de volta pra casa.",
            "Ser nordestino fora do Nordeste é descobrir o tamanho da própria raiz.",
            "Tem distância que enfraquece costume. A minha só aumentou o orgulho.",
            "Se perguntarem de onde eu sou, provavelmente a playlist responde primeiro.",
            "A Europa mudou meu endereço. O Nordeste continua mudando meu humor.",
            "Tem identidade que não precisa de bandeira. Basta abrir a boca ou dar play.",
            "Nordestino reconhece o outro até no jeito de sentir uma música.",
            "Morar longe me ensinou uma coisa: origem não fica pra trás, viaja junto.",
        ],
        "captions": [
            "Ser nordestino longe de casa tem dessas: qualquer detalhe certo vira passagem de volta por alguns segundos.",
            "Meu endereço pode mudar quantas vezes quiser. Tem coisa que continua falando de onde eu vim.",
            "Qual detalhe do Nordeste você reconheceria de olhos fechados? Eu começo pela música.",
            "A distância fez muita coisa mudar. O orgulho de ser nordestino foi justamente na direção contrária.",
            "Quem mora fora sabe o valor que um sotaque conhecido ganha no meio de um monte de voz diferente.",
            "Não é romantizar origem. É perceber que cultura vira referência quando o resto muda ao redor.",
            "Se você é nordestino e mora longe, comenta teu estado. Quero ver até onde essa turma chegou.",
            "Tem coisa que a gente só entende quando sai de casa: o quanto a origem participa de quem a gente virou.",
            "O bom de ser nordestino é que até saudade vem com música, comida, expressão e história.",
            "Qual música entrega teu estado antes mesmo de você falar de onde é?",
            "Eu não preciso morar no Nordeste pra continuar levando um pedaço dele comigo.",
            "A melhor parte de viajar o mundo é perceber que raiz forte não atrapalha caminho; dá direção."
        ],
    },
    "brasileiro_exterior": {
        "overlays": [
            "Morar fora é ter orgulho da conquista e saudade no mesmo bolso.",
            "A Europa muda muita coisa. O jeito de sentir falta de casa não.",
            "Quem mora fora aprende que saudade também tem rotina.",
            "Tem dia que vencer longe de casa custa mais do que parece no vídeo.",
            "Morar fora é bonito até uma música brasileira acertar no meio do peito.",
            "O passaporte abre portas. A saudade continua sabendo onde você mora.",
            "A vida fora ensina independência e cobra presença em momentos que você perde.",
            "Tem conquista que a gente comemora sorrindo e pensando em quem ficou longe.",
            "Morar fora é aprender a chamar dois lugares diferentes de casa.",
            "O país mudou. Algumas referências continuam falando português.",
            "Quem emigra descobre que distância não se mede só em quilômetros.",
            "Tem dia que a Irlanda parece perto. Tem música que faz o Brasil parecer muito longe.",
            "A gente vai buscar futuro e acaba entendendo melhor o passado.",
            "Morar fora é ganhar mundo sem conseguir levar todo mundo junto.",
            "Tem coisa que só ganha valor depois que deixa de estar por perto.",
            "Eu aprendi muita coisa morando fora. Sentir falta de detalhes foi uma delas.",
            "A vida no exterior tem oportunidade, boleto, saudade e muito improviso.",
            "Quem vê a paisagem nem sempre vê o preço emocional da mudança.",
        ],
        "captions": [
            "Morar fora não é só foto bonita nem sofrimento. É esse pacote estranho de conquista, rotina e saudade acontecendo junto.",
            "Qual coisa simples do Brasil você só percebeu que amava depois que foi morar fora?",
            "Tem dia que a gente se sente muito longe. Em outros, basta uma música pra trazer tudo pra perto.",
            "Eu gosto da vida que construí fora, mas seria mentira dizer que não existem coisas que pesam diferente com a distância.",
            "Quem emigrou sabe: cada conquista tem um lado que aparece na foto e outro que só a gente conhece.",
            "Morar fora também é criar novas referências sem abandonar as antigas.",
            "O que mais te surpreendeu depois de sair do Brasil? Pra mim, foi o tamanho que certas coisas pequenas ganham.",
            "Tem gente que pensa que morar fora é começar do zero. Na prática, você leva muita coisa antiga junto.",
            "A distância muda a rotina, mas algumas músicas fazem questão de manter a memória atualizada.",
            "Qual cidade brasileira ainda parece casa pra você, mesmo morando longe?",
            "A experiência de emigrar fica mais real quando a gente fala das partes boas e das partes cansativas também.",
            "Se você mora fora, provavelmente já sentiu orgulho e vontade de voltar no mesmo dia."
        ],
    },
    "generic": {
        "overlays": [
            "Terapia do dia: essa música e cinco minutos sem explicar nada.",
            "Eu ia passar o vídeo. A música claramente tinha outros planos.",
            "Tem música que chega antes da gente saber que tava precisando.",
            "Essa parte aqui merece mais atenção do que muita conversa por aí.",
            "A cabeça tava em outro lugar até essa voz entrar.",
            "Se você ficou até aqui, provavelmente não foi por causa do algoritmo.",
            "Tem refrão que funciona melhor quando pega a gente desprevenido.",
            "Eu gosto de música que me faz esquecer por que peguei o celular.",
            "Essa foi daquelas que transformam rolagem em pausa.",
            "Tem dia que a melhor decisão é só deixar a música terminar.",
            "Eu não sei o que essa música te lembra. Em mim, ela mexeu aqui.",
            "A voz entrou e minha atenção desistiu de ir embora.",
            "Nem toda música precisa de contexto. Algumas só precisam de volume.",
            "Isso aqui tem cara de música que alguém vai mandar sem explicar nada.",
            "Se a letra bater diferente, finge que foi só coincidência.",
            "A música é curta. O tanto de coisa que ela puxa da cabeça não.",
            "Tem som que você escuta. E tem som que muda teu jeito de ficar quieto.",
            "Eu vim cantar. A música resolveu conversar com quem tava ouvindo.",
            "Se isso te fez lembrar de alguém, a responsabilidade é do compositor.",
            "Meu tipo favorito de música é a que faz a gente parar sem perceber.",
            "Não sei se é nostalgia, terapia ou só uma música boa. Aceito os três.",
            "Se essa parte não te pegou, espera o próximo verso antes de julgar.",
            "Tem música que pede replay antes mesmo de terminar.",
            "Hoje eu só queria cantar. Se virou terapia, foi consequência.",
        ],
        "captions": [
            "Eu gosto quando a música segura a pessoa sem precisar inventar efeito, texto ou promessa. Só a música mesmo.",
            "Se você parou a rolagem por causa da voz, me diz qual detalhe te fez ficar.",
            "Tem dia que eu posto pra cantar. Em outros, percebo que a música acaba falando com alguém do outro lado.",
            "Qual foi a última música que fez você esquecer o que tava fazendo por alguns segundos?",
            "Eu não quero te convencer a gostar. Só deixa essa parte terminar e decide depois.",
            "Essa entrou na categoria: não precisava ouvir hoje, mas ainda bem que ouvi.",
            "Se te lembrou alguém, um lugar ou uma fase, comenta só uma palavra. Quero ver as histórias que aparecem.",
            "Algumas músicas funcionam melhor sem legenda explicando demais. Essa é uma delas.",
            "Eu ia escrever uma reflexão enorme, mas o refrão já fez o serviço. 😂",
            "Se ficou até o final, escolhe a próxima terapia musical nos comentários.",
            "Tem voz que impressiona pela técnica. Tem voz que prende porque parece verdade. Eu fico com a segunda.",
            "O melhor tipo de vídeo é aquele em que a música faz você esquecer que tava só passando o tempo."
        ],
    },
}


def unique(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = " ".join(str(value).split()).strip()
        if clean and clean not in seen:
            out.append(clean)
            seen.add(clean)
    return out


def main() -> None:
    copy_bank = json.loads(VIRAL_COPY.read_text(encoding="utf-8"))
    profiles = json.loads(PROFILES.read_text(encoding="utf-8")) if PROFILES.exists() else {}
    curated = profiles.get("themes", {})

    for theme, library in AUTHORIAL.items():
        section = copy_bank.setdefault(theme, {})
        profile_items = curated.get(theme, [])
        profile_overlays = [item.get("overlay", "") for item in profile_items]
        profile_captions = [item.get("caption", "") for item in profile_items]

        overlays = unique(profile_overlays + library["overlays"])
        captions = unique(profile_captions + library["captions"])

        # A frase precisa parecer escrita para o vídeo, não um encaixe de template.
        # Eliminamos as combinações automáticas nos temas principais e usamos linhas fechadas.
        section["overlays"] = overlays
        section["captions"] = captions
        section.pop("overlays_templates", None)
        section.pop("overlays_endings", None)
        section.pop("captions_templates", None)
        section.pop("captions_endings", None)

    VIRAL_COPY.write_text(
        json.dumps(copy_bank, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    render_source = RENDER.read_text(encoding="utf-8")
    old = "safe_centers = (0.13, 0.25, 0.68, 0.78)"
    new = "safe_centers = (0.22, 0.32, 0.66, 0.76)"
    if old in render_source:
        render_source = render_source.replace(old, new, 1)
    elif new not in render_source:
        raise RuntimeError("Não encontrei a geometria esperada para ajustar a altura do texto")
    RENDER.write_text(render_source, encoding="utf-8")

    print(
        "Estilo aplicado: frases autorais sem templates nos temas principais; "
        "primeira posição livre movida de 13% para 22% da altura."
    )


if __name__ == "__main__":
    main()
