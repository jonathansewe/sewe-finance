/**
 * Every language file must have exactly the same keys and placeholders.
 * A key missing in fr.json would show raw English (or the key) to French
 * users; this test catches it before merge (SPEC 9, CI step).
 */

import { LANGUAGES, resources } from '@/i18n';

type Tree = { [key: string]: string | Tree };

function flatten(tree: Tree, prefix = ''): Record<string, string> {
  return Object.entries(tree).reduce<Record<string, string>>((flat, [key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    return typeof value === 'string' ? { ...flat, [path]: value } : { ...flat, ...flatten(value, path) };
  }, {});
}

const placeholders = (text: string) => (text.match(/{{\s*\w+\s*}}/g) ?? []).sort();

const files = resources as Record<string, Tree>;
const english = flatten(files.en);

it('every language in LANGUAGES has a file in resources', () => {
  expect(Object.keys(files).sort()).toEqual([...LANGUAGES].sort());
});

describe.each(LANGUAGES.filter((lang) => lang !== 'en'))('%s.json', (lang: string) => {
  const other = flatten(files[lang]);

  it('has exactly the same keys as en.json', () => {
    expect(Object.keys(other).sort()).toEqual(Object.keys(english).sort());
  });

  it('uses the same {{placeholders}} as en.json in every string', () => {
    for (const key of Object.keys(english)) {
      expect({ key, vars: placeholders(other[key] ?? '') }).toEqual({ key, vars: placeholders(english[key]) });
    }
  });

  it('has no empty strings', () => {
    expect(Object.entries(other).filter(([, v]) => v.trim() === '')).toEqual([]);
  });
});
