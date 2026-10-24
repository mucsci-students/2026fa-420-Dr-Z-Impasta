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
		this.prevDoc = this.doc;
	}

	set(newDoc) {
		this.prevDoc = this.doc;
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

	constructor(originator) {
		this.snapshots = originator.doc == null ? [] : [originator.storeFile()];
	}

	push(memento) {
		if (!(memento instanceof ConfigFileMemento))
			throw new TypeError("Expected a valid configuration file");

		this.snapshots.push(memento);
	}

	pop() {
		return this.snapshots.pop();
	}

	getMemento(index) {
		return this.snapshots[index];
	}
}


export { ConfigFileMemento, ConfigFileOriginator, ConfigFileHistory };
