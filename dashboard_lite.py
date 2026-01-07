import profit_config as cfg
import json
import os
from neo4j import GraphDatabase

# --- MOBILE-FIRST HTML TEMPLATE ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>ProfitGraph Strategy Room</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        body { margin: 0; padding: 0; background: #000; color: #0f0; font-family: monospace; overflow: hidden; height: 100vh; width: 100vw; }
        
        /* LAYOUT: Top 60% Graph, Bottom 40% Info */
        #network { 
            width: 100vw; 
            height: 60vh; 
            border-bottom: 2px solid #333; 
            background: #111;
        }
        
        #panel { 
            width: 100vw; 
            height: 40vh; 
            background: #000; 
            padding: 15px; 
            box-sizing: border-box; 
            overflow-y: auto; 
            position: absolute; 
            bottom: 0;
            left: 0;
            border-top: 1px solid #0f0;
        }

        /* TYPOGRAPHY */
        h2 { margin: 0 0 10px 0; color: #fff; font-size: 1.2rem; border-bottom: 1px solid #333; padding-bottom: 5px; }
        p { margin: 5px 0; color: #ccc; font-size: 0.9rem; line-height: 1.4; }
        strong { color: #0f0; }
        
        /* BADGES */
        .badge { display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; font-weight: bold; margin-bottom: 8px; }
        .risk { border: 1px solid #ff4444; color: #ff4444; }
        .tool { border: 1px solid #0f0; color: #0f0; }
        .strategy { border: 1px solid #00ccff; color: #00ccff; }
        
        /* HINT TEXT */
        .hint { color: #555; text-align: center; margin-top: 20px; font-style: italic; }
    </style>
</head>
<body>
    <div id="network"></div>
    <div id="panel">
        <div id="content-area">
            <p class="hint">Tap a node to reveal intelligence...</p>
        </div>
    </div>

    <script type="text/javascript">
        var nodes = new vis.DataSet(__NODES__);
        var edges = new vis.DataSet(__EDGES__);

        var container = document.getElementById('network');
        var data = { nodes: nodes, edges: edges };
        
        // MOBILE OPTIMIZED SETTINGS
        var options = {
            nodes: {
                shape: 'dot',
                size: 20,
                font: { color: '#ffffff', size: 14, strokeWidth: 2, strokeColor: '#000' },
                borderWidth: 2,
                shadow: true
            },
            edges: {
                width: 1,
                color: { color: '#444', highlight: '#0f0' },
                selectionWidth: 3
            },
            interaction: {
                hover: false, 
                tooltipDelay: 200,
                zoomView: true,
                dragView: true
            },
            physics: {
                stabilization: false,
                barnesHut: { gravitationalConstant: -10000, springLength: 150 }
            },
            groups: {
                Strategy: { color: '#00ccff', size: 30 },
                Tool: { color: '#00ff00' },
                Risk: { color: '#ff4444', shape: 'triangle', size: 25 },
                Entity: { color: '#ffff00' }
            }
        };

        var network = new vis.Network(container, data, options);

        // CLICK HANDLER
        network.on("click", function (params) {
            var contentDiv = document.getElementById('content-area');
            
            if (params.nodes.length > 0) {
                // User tapped a node
                var nodeId = params.nodes[0];
                var node = nodes.get(nodeId);
                
                var badgeClass = "";
                if(node.group === "Risk") badgeClass = "risk";
                else if(node.group === "Strategy") badgeClass = "strategy";
                else badgeClass = "tool";

                var html = "<h2>" + node.label + "</h2>";
                html += "<span class='badge " + badgeClass + "'>" + node.group + "</span>";
                
                if (node.detail) {
                    html += "<p><strong>Details:</strong> " + node.detail + "</p>";
                }
                if (node.content) {
                    html += "<p><strong>Strategy Brief:</strong><br>" + node.content.replace(/\\n/g, '<br>') + "</p>";
                }
                
                contentDiv.innerHTML = html;
            } else {
                // User tapped empty space
                contentDiv.innerHTML = '<p class="hint">Tap a node to reveal intelligence...</p>';
            }
        });
    </script>
</body>
</html>
"""

def generate_dashboard():
    print(f"🔌 Generating Mobile Dashboard...")
    
    driver = GraphDatabase.driver(cfg.NEO4J_URI, auth=cfg.NEO4J_AUTH)
    with driver.session() as session:
        # Fetch Nodes
        print("   - Downloading Intelligence...")
        query = """
        MATCH (n) 
        RETURN id(n) as id, labels(n) as labels, n.name as name, 
               n.detail as detail, n.content as content
        """
        result_nodes = session.run(query)
        nodes = []
        for r in result_nodes:
            lbl = r["labels"][0] if r["labels"] else "Entity"
            display_label = r["name"]
            if not display_label and lbl == "Strategy": display_label = "Strategy Node"
            if not display_label: display_label = f"{lbl}"
            
            nodes.append({
                "id": r["id"], 
                "label": display_label, 
                "group": lbl,
                "detail": r["detail"] if r["detail"] else "",
                "content": r["content"][:1000] + "..." if r["content"] else "" 
            })

        # Fetch Edges
        result_edges = session.run("MATCH (n)-[r]->(m) RETURN id(n) as from, id(m) as to")
        edges = [{"from": r["from"], "to": r["to"]} for r in result_edges]

    driver.close()

    html_content = HTML_TEMPLATE.replace("__NODES__", json.dumps(nodes)).replace("__EDGES__", json.dumps(edges))
    output_path = os.path.join(cfg.DOWNLOADS_DIR, "profit_graph_mobile.html")
    
    with open(output_path, "w") as f:
        f.write(html_content)

    print(f"✅ Mobile Dashboard Ready: {output_path}")

if __name__ == "__main__":
    generate_dashboard()
