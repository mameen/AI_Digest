'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { deployMode, isPagesReadonly, isDeployedViewOnly, canTune, tuningLocked, splitConfigYaml } =
  require('../admin/admin-app.js');
const fs = require('node:fs');
const path = require('node:path');

test('deployMode detects GitHub Pages host', () => {
  assert.equal(deployMode({ hostname: 'mameen.github.io', protocol: 'https:' }), 'pages');
  assert.equal(deployMode({ hostname: 'foo.github.io', protocol: 'https:' }), 'pages');
});

test('deployMode detects local admin server', () => {
  assert.equal(deployMode({ hostname: '127.0.0.1', protocol: 'http:' }), 'local');
});

test('isDeployedViewOnly on github.io', () => {
  global.window = { __ADMIN_READONLY__: true, location: { hostname: 'mameen.github.io', protocol: 'https:' } };
  assert.equal(isDeployedViewOnly(), true);
  assert.equal(isPagesReadonly(), true);
});

test('isPagesReadonly is false on localhost', () => {
  global.window = { __ADMIN_READONLY__: false, location: { hostname: '127.0.0.1', protocol: 'http:' } };
  assert.equal(isPagesReadonly(), false);
});

test('canTune requires branch off main with live API', () => {
  global.window = { __ADMIN_READONLY__: false, location: { hostname: '127.0.0.1', protocol: 'http:' } };
  assert.equal(canTune(), false);
  assert.equal(tuningLocked(), false);
});

test('splitConfigYaml fills enrich and publish sections', () => {
  const yaml = fs.readFileSync(path.join(__dirname, '..', 'config.yaml'), 'utf8');
  const sections = splitConfigYaml(yaml);
  assert.match(sections.pipeline, /^run:/m);
  assert.match(sections.enrich, /^llm:/m);
  assert.match(sections.enrich, /^enrich:/m);
  assert.match(sections.publish, /^validation:/m);
  assert.ok(sections.enrich.length > 50);
});
