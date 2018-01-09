def get_siren(siret):
    return siret[:9]


def get_nic(siret):
    return siret[9:]
