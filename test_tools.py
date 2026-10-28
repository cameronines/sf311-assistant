from tools import count_requests, recent_similar_requests, typical_resolution_time

print(count_requests("Graffiti Public", "Mission", 30))
print()
print(recent_similar_requests("Street and Sidewalk Cleaning", "Mission", 7, 5))
print()
print(typical_resolution_time("Graffiti Public", "Mission"))


print()
print(recent_similar_requests("Street and Sidewalk Cleaning", "Mission", 14, 5, street="16th Street"))

try:
    recent_similar_requests("Noise", "Mission", street="16th'; --")
except ValueError as e:
    print("Blocked as expected:", e)