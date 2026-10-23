from tools import count_requests, recent_similar_requests, typical_resolution_time

print(count_requests("Graffiti Public", "Mission", 30))
print()
print(recent_similar_requests("Street and Sidewalk Cleaning", "Mission", 7, 5))
print()
print(typical_resolution_time("Graffiti Public", "Mission"))