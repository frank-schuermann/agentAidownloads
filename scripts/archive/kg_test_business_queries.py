from core.knowledge_graph.service import KnowledgeGraphService

kg = KnowledgeGraphService("tenant_demo")

print("Affected customers of svc_payment:")
print(kg.get_affected_customers("svc_payment"))

print("SLA exposure for svc_payment:")
print(kg.get_customer_sla_exposure("svc_payment"))

print("Features affected by svc_payment:")
print(kg.get_features_affected_by_service("svc_payment"))

print("Product impact for svc_payment:")
print(kg.get_product_impact("svc_payment"))
