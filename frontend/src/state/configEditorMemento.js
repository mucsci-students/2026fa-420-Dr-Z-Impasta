// TODO: add error handling for non-combined-config-compliant files
class ConfigFileMemento {

	constructor(doc) {
		this.doc = structuredClone(doc);
	}

	getFile() {
		return this.doc;
	}

}

class ConfigFileOriginator {

	constructor() {
		this.doc = null;
	}

	set(newDoc) {
		this.doc = newDoc;
	}

	storeFile() {
		return new ConfigFileMemento(this.doc);
	}

	restore(memento) {
		this.doc = memento.getFile();
	}

}

class ConfigFileHistory {

	constructor() {
		this.snapshots = [];
	}

	push(memento) {
		if (!(memento instanceof ConfigFileMemento))
			throw new TypeError("Expected a valid configuration file");

		this.snapshots.push(memento.getFile());
	}

	pop() {
		return this.snapshots.pop();
	}

	getMemento(index) {
		return this.snapshots[index];
	}
}


export { ConfigFileMemento, ConfigFileOriginator, ConfigFileHistory };
