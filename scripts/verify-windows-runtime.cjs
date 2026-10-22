// Verify the complete builder output against the pinned upstream PE, allowing
// only the ASAR integrity resource generated from this build's actual archive.
const fs = require('node:fs/promises');
const path = require('node:path');
const { createHash } = require('node:crypto');
const { createRequire } = require('node:module');
const dependency = createRequire(path.resolve(__dirname, '../desktop/package.json'));
const { NtExecutable, NtExecutableResource, Resource } = dependency('resedit');
const { readAsarHeader } = dependency('app-builder-lib/out/asar/asar');
const digest = data => createHash('sha256').update(data).digest('hex');

async function canonicalRuntime(vendor, asar) {
  const executable = NtExecutable.from(vendor);
  const resources = NtExecutableResource.from(executable);
  const versions = Resource.VersionInfo.fromEntries(resources.entries);
  if (versions.length !== 1) throw new Error('Unexpected upstream version resources');
  const languages = versions[0].getAllLanguagesForStringValues();
  if (languages.length !== 1) throw new Error('Unexpected upstream resource languages');
  const { header } = await readAsarHeader(asar);
  const headerHash = digest(header);
  resources.entries.push({ type: 'INTEGRITY', id: 'ELECTRONASAR',
    bin: Buffer.from(JSON.stringify([{ file: 'resources\\app.asar', alg: 'SHA256', value: headerHash }])),
    lang: languages[0].lang, codepage: languages[0].codepage });
  resources.outputResource(executable);
  return { bytes: Buffer.from(executable.generate()), headerHash };
}
async function verify(vendorPath, appPath) {
  const asar = path.join(path.dirname(appPath), 'resources/app.asar');
  return verifyBytes(await fs.readFile(vendorPath), await fs.readFile(appPath), asar);
}
async function verifyBytes(vendor, actual, asar) {
  const manifest = JSON.parse(await fs.readFile(path.resolve(__dirname, '../desktop/vendor-runtime.json'), 'utf8'));
  if (digest(vendor) !== manifest.executable_sha256) throw new Error('Upstream executable SHA256 mismatch');
  const expected = await canonicalRuntime(vendor, asar);
  if (digest(actual) !== digest(expected.bytes)) throw new Error('Builder changed the runtime beyond its ASAR integrity resource');
  return { asar_header_sha256: expected.headerHash, app_asar_sha256: digest(await fs.readFile(asar)), builder_executable_sha256: digest(actual) };
}
module.exports = { canonicalRuntime, verify, verifyBytes };
if (require.main === module) verify(...process.argv.slice(2)).then(value => console.log(JSON.stringify(value))).catch(error => { console.error(error.message); process.exitCode = 1; });
