import pathlib

ENV = pathlib.Path(r"C:\Users\19024\Documents\ecommerce-hot\AIHOT\.env")

# bcrypt hash for the edge admin password; compose interpolates '$', so each one is doubled
raw_hash = "$2a$14$VpdwKsJmMRuYJGnJz6DmFe6zLv6gID4FGqzRylvV5Qyuu8.gcFfqG"
escaped = raw_hash.replace("$", "$$")

text = ENV.read_text(encoding="utf-8")
lines = [ln for ln in text.splitlines() if not ln.startswith("EDGE_ADMIN_")]
lines.append("# public edge: /admin basic auth (user: ecadmin)")
lines.append("EDGE_ADMIN_PASSWORD=OHlzKGkdiESGEp61")
lines.append("EDGE_ADMIN_HASH=" + escaped)
ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")

print("hash line written, escaped =", escaped[:20], "...")
