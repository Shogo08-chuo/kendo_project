import matplotlib.pyplot as plt


def create_counts_figure(counts: dict[str, int]):
    fig, ax = plt.subplots(figsize=(10, 5))
    labels = ["Men", "Kote", "Do"]
    values = [counts.get("men", 0), counts.get("kote", 0), counts.get("do", 0)]
    colors = ["#d33f49", "#1769aa", "#f6aa1c"]

    ax.bar(labels, values, color=colors)
    ax.set_ylabel("検出回数")
    ax.set_title("技別スタッツ")
    ax.set_ylim(bottom=0)
    return fig
