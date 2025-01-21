import openrouteservice
import acopy
import networkx as nx

# Inicialize o cliente da API
api_key = "5b3ce3597851110001cf62489d3e6533087b48feb2a42b8257032d98"
client = openrouteservice.Client(key=api_key)

# Defina as coordenadas (longitude, latitude)
distribuidoras = {"D01":(-43.937242870996386, -19.953830433265118), "D02":(-43.93468990837559, -19.90106819264693),
                  "D03":(-44.06005761164899, -19.858314000857856), "D04":(-44.02073040945838, -19.959911682520648),
                  "D05":(-43.93216814709734, -19.84177974124646)
}
clientes = {
    "C01": (-43.914838, -19.904836), "C02": (-43.961736, -19.91761), "C03": (-44.029132, -19.835967), "C04": (-44.025341, -19.830902),
    "C05": (-43.937357, -19.939277), "C06": (-43.97087, -19.932878), "C07": (-44.007843, -19.940873), "C08": (-43.981024, -19.847281),
    "C09": (-43.987711, -19.877455), "C10": (-44.004315, -19.951052), "C11": (-43.985634, -19.851745), "C12": (-43.946908, -19.83222),
    "C13": (-43.980987, -19.922795), "C14": (-43.988459, -19.904761), "C15": (-43.955843, -19.927421), "C16": (-43.970831, -19.84132),
    "C17": (-43.994115, -19.870325), "C18": (-43.933808, -19.834543), "C19": (-44.01275, -19.901827), "C20": (-43.931933, -19.901662),
    "C21": (-44.004627, -19.889491), "C22": (-44.017062, -19.840566), "C23": (-43.964456, -19.934946), "C24": (-43.946312, -19.827317),
    "C25": (-43.932281, -19.930534), "C26": (-43.984054, -19.855395), "C27": (-43.930969, -19.90302), "C28": (-43.956209, -19.925759),
    "C29": (-43.99004, -19.885818), "C30": (-43.928424, -19.917033), "C31": (-43.966006, -19.82657), "C32": (-43.986458, -19.948096),
    "C33": (-43.958541, -19.846364), "C34": (-43.925626, -19.900943), "C35": (-43.92619, -19.936039), "C36": (-43.964471, -19.829429),
    "C37": (-43.990049, -19.908601), "C38": (-43.977673, -19.917083), "C39": (-44.022812, -19.852453), "C40": (-43.95416, -19.902797),
    "C41": (-44.02575, -19.947638), "C42": (-43.940295, -19.914534), "C43": (-43.970145, -19.839723), "C44": (-43.981108, -19.920487),
    "C45": (-43.948312, -19.89904), "C46": (-43.926583, -19.909907), "C47": (-43.931027, -19.932165), "C48": (-43.98899, -19.845746),
    "C49": (-43.96817, -19.857176), "C50": (-44.027854, -19.851525)
}

# Função para calcular a matriz de distâncias entre as distribuidoras e os clientes
def calcular_matriz_distancias(client, distribuidoras, clientes):
    # Formatar coordenadas para o formato aceito pela API
    locations = list(distribuidoras.values()) + list(clientes.values())
    try:
        # Chamar a API para obter a matriz de distâncias
        response = client.distance_matrix(
            locations=locations,
            profile="driving-car",
            metrics=["distance"],  # Utilizar distância
            units="m"
        )
        return response
    except openrouteservice.exceptions.ApiError as e:
        print(f"Erro na API: {e}")
        return None

# Função para atribuir clientes às distribuidoras mais próximas
def atribuir_clientes_a_distribuidoras(matrix, distribuidoras, clientes):
    resultado = {dist_id: [] for dist_id in distribuidoras.keys()}

    # Obter IDs de distribuidoras e clientes
    distribuidoras_ids = list(distribuidoras.keys())
    clientes_ids = list(clientes.keys())

    # Iterar pelos clientes
    for j, cliente_id in enumerate(clientes_ids):
        distancias_cliente = [
            (distribuidoras_ids[i], matrix["distances"][j + len(distribuidoras)][i])
            for i in range(len(distribuidoras))
        ]

        # Encontrar a distribuidora mais próxima
        distribuidora_mais_proxima = min(distancias_cliente, key=lambda x: x[1])[0]
        resultado[distribuidora_mais_proxima].append(cliente_id)

    return resultado

def calcular_melhor_rota(dicionario_distribuicao, matriz_distancias, distrib, client):
    rotas = {}
    for distribuidora, clientes in dicionario_distribuicao.items():
        if not clientes:
            rotas[distribuidora] = {"rota": [], "distancia_total": 0}
            continue

        # Construir grafo para o solver
        grafo = nx.Graph()
        pontos = [distribuidora] + clientes
        indices = {p: i for i, p in enumerate(list(distrib.keys()) + list(client.keys()))}
        for i, ponto1 in enumerate(pontos):
            for j, ponto2 in enumerate(pontos):
                if i != j:
                    dist = matriz_distancias["distances"][indices[ponto1]][indices[ponto2]]
                    grafo.add_edge(ponto1, ponto2, weight=dist)

        # Configurar o solver da colônia de formigas
        # solver = acopy.Solver(rho=0.1, q=1)
        # colônia = acopy.Colony(alpha=1, beta=3)
        solver = acopy.Solver(rho=0.2, q=2)  # Ajuste de rho e q
        colonia = acopy.Colony(alpha=1, beta=2)  # Ajuste de alpha e beta

        # Resolver o TSP
        tour = solver.solve(grafo, colonia, limit=200)
        rota = list(tour.nodes)

        # Garantir que a distribuidora seja o ponto inicial e o final
        if rota[0] != distribuidora:
            distribuidora_index = rota.index(distribuidora)
            rota = rota[distribuidora_index:] + rota[:distribuidora_index]
        rota.append(distribuidora)

        # Calcular a distância total da rota ajustada
        distancia_total = sum(
            grafo[rota[i]][rota[i + 1]]["weight"]
            for i in range(len(rota) - 1)
        )

        # Salvar a rota ajustada e a distância total
        rotas[distribuidora] = {"rota": rota, "distancia_total": distancia_total}
    return rotas

# Função principal para executar o algoritmo múltiplas vezes e selecionar a melhor solução
def executar_multipla_execucao(dicionario_distribuicao, matriz_distancias, distrib, client, num_execucoes=5):
    rotas_otimizadas = {}

    # Laço para realizar múltiplas execuções do algoritmo
    for _ in range(num_execucoes):

        # Chama a função que calcula a rota para cada distribuidora
        rotas = calcular_melhor_rota(dicionario_distribuicao, matriz_distancias, distrib, client)

        # Comparar com as melhores rotas já armazenadas e selecionar a melhor
        if not rotas_otimizadas:
            rotas_otimizadas = rotas
        else:
            for distribuidora, dados in rotas.items():
                if dados['distancia_total'] < rotas_otimizadas[distribuidora]['distancia_total']:
                    rotas_otimizadas[distribuidora] = dados
    return rotas_otimizadas

# Calcular a matriz de distâncias
matriz_distancias = calcular_matriz_distancias(client, distribuidoras, clientes)

# Verificar se a matriz foi calculada corretamente
if matriz_distancias:
    # Atribuir clientes às distribuidoras mais próximas
    distribuidores_proximos = atribuir_clientes_a_distribuidoras(matriz_distancias, distribuidoras, clientes)

    # Exibir resultado
    for distribuidora, clientes_proximos in distribuidores_proximos.items():
        print(f"Distribuidora {distribuidora}: Clientes {clientes_proximos}")

    # Calcular o melhor trajeto para cada distribuidora
    rotas_otimizadas = executar_multipla_execucao(distribuidores_proximos, matriz_distancias, distribuidoras, clientes, num_execucoes=10)
    print("Rotas otimizadas:", rotas_otimizadas)
    for distribuidora, dados in rotas_otimizadas.items():
        print(f"Distribuidora {distribuidora}:")
        print(f"  Rota: {dados['rota']}")
        print(f"  Distância Total: {dados['distancia_total']} metros")