/**
 * Fetches device metadata including IP and Geo-location.
 * Stubbed for user privacy to comply with Edge Add-ons store policies.
 * @returns {Promise<Object>} Metadata object: { ip, city, country, region }
 */
export async function getDeviceMetadata() {
  return {
    ip: '127.0.0.1',
    city: 'Local',
    country: 'Privacy Mode',
    region: 'Active'
  };
}
