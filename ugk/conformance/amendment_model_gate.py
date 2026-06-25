"""ugk/conformance/amendment_model_gate.py — AMD-S-02: amendment-model-at-inception. GATE_GROUP = "integration" """


def run():
    from ugk.charter import DeploymentManifest
    from ugk.conformance._fixture import fixture_pubkey
    fails = []
    pub = fixture_pubkey()

    m = DeploymentManifest.create(pub)
    if m.amendment_model != "higher_root":
        fails.append(f"UGK default amendment_model={m.amendment_model!r}, expected 'higher_root'")
    if m.amendment_model not in ("higher_root", "self"):
        fails.append(f"amendment_model {m.amendment_model!r} not in enum {{higher_root, self}}")
    if not m.verify_hash():
        fails.append("manifest_hash does not verify (amendment_model not committed)")
    if "amendment_model" not in m.to_dict():
        fails.append("amendment_model absent from manifest to_dict()")

    # committed in manifest_hash: changing the declared model changes the hash
    m_self = DeploymentManifest.create(pub, amendment_model="self")
    if m_self.manifest_hash == m.manifest_hash:
        fails.append("amendment_model not committed in manifest_hash (higher_root vs self collide)")
    if not m_self.verify_hash():
        fails.append("'self' model manifest does not verify")

    ok = not fails
    return ok, (
        "AMD-S-02: DeploymentManifest declares amendment_model in {higher_root, self} at inception; "
        "UGK = higher_root; committed in manifest_hash (changing it changes the hash)."
        if ok else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"amendment_model_gate: {'PASS' if ok else 'FAIL'}  {detail}")
