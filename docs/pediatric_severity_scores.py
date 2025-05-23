
# Pediatric Illness Severity Scoring Functions

def calculate_pews(respiratory_rate, respiratory_effort, oxygen_use, heart_rate, cap_refill, behavior):
    score = 0
    if respiratory_rate > 40: score += 2
    if respiratory_effort == 'increased': score += 2
    if oxygen_use == 'yes': score += 2
    if heart_rate > 130: score += 2
    if cap_refill > 2: score += 1
    if behavior in ['irritable', 'lethargic']: score += 2
    return score

def calculate_trap(respiratory_support, hemodynamic_stability, neuro_status, access_difficulty):
    score = 0
    if respiratory_support in ['BiPAP', 'intubated']: score += 2
    if hemodynamic_stability == 'unstable': score += 2
    if neuro_status in ['altered', 'seizure']: score += 2
    if access_difficulty == 'yes': score += 1
    return score

def calculate_cameo2(physiologic_instability, intervention_level, nursing_dependency):
    score = 0
    if physiologic_instability == 'high': score += 3
    elif physiologic_instability == 'moderate': score += 2
    if intervention_level == 'complex': score += 3
    elif intervention_level == 'moderate': score += 2
    if nursing_dependency == 'high': score += 3
    elif nursing_dependency == 'moderate': score += 2
    return score

def calculate_prism3(vitals, labs):
    score = 0
    if vitals['SBP'] < 70: score += 4
    if vitals['GCS'] < 8: score += 4
    if labs['pH'] < 7.2: score += 4
    if labs['creatinine'] > 1.5: score += 2
    if labs['WBC'] < 4 or labs['WBC'] > 20: score += 2
    return score

def calculate_queensland_non_trauma(resp_rate, HR, mental_status, SpO2):
    score = 0
    if resp_rate > 50: score += 2
    if HR > 140: score += 2
    if mental_status != 'alert': score += 2
    if SpO2 < 92: score += 2
    return score

def calculate_queensland_trauma(mechanism, consciousness, airway, breathing, circulation):
    score = 0
    if mechanism in ['high-speed MVC', 'fall >3m']: score += 2
    if consciousness in ['GCS<13']: score += 2
    if airway == 'compromised': score += 2
    if breathing == 'abnormal': score += 2
    if circulation == 'poor perfusion': score += 2
    return score
