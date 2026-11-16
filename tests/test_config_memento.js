import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { 
	ConfigFileMemento, 
	ConfigFileOriginator, 
	ConfigFileHistory 
} from "../frontend/src/state/configEditorMemento.js";

// Relative to this file, not the folder the test is run from.
const CONFIG_FILE = JSON.parse(
	fs.readFileSync(new URL("../examples/sample_config.json", import.meta.url), 'utf-8')
);

test("test config file memento", () => {
	const mem = new ConfigFileMemento(CONFIG_FILE);
	assert.deepEqual(mem.doc, CONFIG_FILE);
});

test("test config file originator", () => {
	const org = new ConfigFileOriginator();

	// A new originator holds "" (no file yet); ConfigFileHistory checks for exactly that.
	org.storeFile();
	assert.deepEqual(org.doc, "");

	org.set(CONFIG_FILE);
	assert.deepEqual(org.doc, CONFIG_FILE);

	org.restore(new ConfigFileMemento(null));
	assert.deepEqual(org.doc, null);

});

test("test config file history", () => {
	const hist = new ConfigFileHistory(new ConfigFileOriginator());
	assert.deepEqual(hist.snapshots, []);

	const memObj = new ConfigFileMemento(CONFIG_FILE);
	hist.push(memObj);
	assert.deepEqual(hist.getMemento(0), memObj);
	assert.deepEqual(hist.getMemento(0).getFile(), CONFIG_FILE);
	assert.deepEqual(hist.snapshots, [memObj]);
	
	assert.deepEqual(hist.getMemento(hist.snapshots.length - 1).getFile(), CONFIG_FILE);
	assert.deepEqual(hist.pop().getFile(), CONFIG_FILE);
	assert.deepEqual(hist.snapshots, [memObj]);


});
