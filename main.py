import openrouteservice
import acopy
import networkx as nx

# Inicialize o cliente da API
api_key = "SUA_CHAVE_AQUI"
client = openrouteservice.Client(key=api_key)

# Dicionários com coordenadas das distribuidoras e clientes
distribuidoras = {
    "D01": (-43.937242870996386, -19.953830433265118),
    "D02": (-43.93468990837559, -19.90106819264693),
    "D03": (-44.06005761164899, -19.858314000857856),
    "D04": (-44.02073040945838, -19.959911682520648),
    "D05": (-43.93216814709734, -19.84177974124646),
}

clientes = {
    "C01": (-43.914838, -19.904836), "C02": (-43.961736, -19.91761),  # ...
    "C03": (-44.029132, -19.835967), "C04": (-44.025341, -19.830902),
    # (... continue com as coordenadas ...)
    "C50": (-44.027854, -19.851525)
}

def calcular_matriz_distancias(client, distribuidoras, clientes):
    locations = list(distribuidoras.values()) + list(clientes.values())
    try:
        response = client.distance_matrix(
            locations=locations,
            profile="driving-car",
            metrics=["distance"],
            units="m"
        )
        return response
    except openrouteservice.exceptions.ApiError as e:
        print(f"Erro na API: {e}")
        return None

def atribuir_clientes_a_distribuidoras(matrix, distribuidoras, clientes):
    resultado = {dist_id: [] for dist_id in distribuidoras.keys()}
    distribuidoras_ids = list(distribuidoras.keys())
    clientes_ids = list(clientes.keys())

    for j, cliente_id in enumerate(clientes_ids):
        distancias_cliente = [
            (distribuidoras_ids[i], matrix["distances"][j + len(distribuidoras)][i])
            for i in range(len(distribuidoras))
        ]
        distribuidora_mais_proxima = min(distancias_cliente, key=lambda x: x[1])[0]
        resultado[distribuidora_mais_proxima].append(cliente_id)

    return resultado

def calcular_melhor_rota(dicionario_distribuicao, matriz_distancias, distrib, cli):
    rotas = {}
    for distribuidora, clientes in dicionario_distribuicao.items():
        if not clientes:
            rotas[distribuidora] = {"rota": [], "distancia_total": 0}
            continue

        grafo = nx.Graph()
        pontos = [distribuidora] + clientes
        indices = {p: i for i, p in enumerate(list(distrib.keys()) + list(cli.keys()))}
        for i, ponto1 in enumerate(pontos):
            for j, ponto2 in enumerate(pontos):
                if i != j:
                    dist = matriz_distancias["distances"][indices[ponto1]][indices[ponto2]]
                    grafo.add_edge(ponto1, ponto2, weight=dist)

        solver = acopy.Solver(rho=0.2, q=2)
        colonia = acopy.Colony(alpha=1, beta=2)

        tour = solver.solve(grafo, colonia, limit=200)
        rota = list(tour.nodes)

        # Ajustar para garantir que a distribuidora seja o ponto inicial e final
        if rota[0] != distribuidora:
            distribuidora_index = rota.index(distribuidora)
            rota = rota[distribuidora_index:] + rota[:distribuidora_index]
        rota.append(distribuidora)

        distancia_total = sum(
            grafo[rota[i]][rota[i + 1]]["weight"] for i in range(len(rota) - 1)
        )

        rotas[distribuidora] = {"rota": rota, "distancia_total": distancia_total}
    return rotas

def executar_multipla_execucao(dicionario_distribuicao, matriz_distancias, distrib, cli, num_execucoes=5):
    rotas_otimizadas = {}
    for _ in range(num_execucoes):
        rotas = calcular_melhor_rota(dicionario_distribuicao, matriz_distancias, distrib, cli)
        if not rotas_otimizadas:
            rotas_otimizadas = rotas
        else:
            for distribuidora, dados in rotas.items():
                if dados['distancia_total'] < rotas_otimizadas[distribuidora]['distancia_total']:
                    rotas_otimizadas[distribuidora] = dados
    return rotas_otimizadas

def main():
    matriz_distancias = calcular_matriz_distancias(client, distribuidoras, clientes)
    if not matriz_distancias:
        print("Não foi possível obter a matriz de distâncias.")
        return

    distrib_assignment = atribuir_clientes_a_distribuidoras(matriz_distancias, distribuidoras, clientes)
    print("Atribuição de clientes às distribuidoras:")
    for distribuidora, lista_clientes in distrib_assignment.items():
        print(f"  {distribuidora}: {lista_clientes}")

    rotas_otimizadas = executar_multipla_execucao(distrib_assignment, matriz_distancias, distribuidoras, clientes, num_execucoes=10)
    print("\nRotas Otimizadas:")
    for distribuidora, dados in rotas_otimizadas.items():
        print(f"  Distribuidora {distribuidora}:")
        print(f"    Rota: {dados['rota']}")
        print(f"    Distância Total: {dados['distancia_total']} metros")

if __name__ == "__main__":
    main()
