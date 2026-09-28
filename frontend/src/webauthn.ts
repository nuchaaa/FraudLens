type Ceremony = { challenge_id: string; public_key: Record<string, unknown> };

function supported(): void {
  if (!window.PublicKeyCredential || !navigator.credentials ||
      !PublicKeyCredential.parseCreationOptionsFromJSON ||
      !PublicKeyCredential.parseRequestOptionsFromJSON) {
    throw new Error("This browser does not support the required security-key API.");
  }
}

export async function registerCredential(ceremony: Ceremony): Promise<Record<string, unknown>> {
  supported();
  const options = PublicKeyCredential.parseCreationOptionsFromJSON(
    ceremony.public_key as unknown as PublicKeyCredentialCreationOptionsJSON,
  );
  const credential = await navigator.credentials.create({ publicKey: options });
  if (!(credential instanceof PublicKeyCredential)) throw new Error("Security-key enrollment was cancelled.");
  return credential.toJSON() as unknown as Record<string, unknown>;
}

export async function authenticateCredential(ceremony: Ceremony): Promise<Record<string, unknown>> {
  supported();
  const options = PublicKeyCredential.parseRequestOptionsFromJSON(
    ceremony.public_key as unknown as PublicKeyCredentialRequestOptionsJSON,
  );
  const credential = await navigator.credentials.get({ publicKey: options });
  if (!(credential instanceof PublicKeyCredential)) throw new Error("Security-key sign-in was cancelled.");
  return credential.toJSON() as unknown as Record<string, unknown>;
}
