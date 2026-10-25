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

	constructor(originator) {
		// snapshots of state of config file before changes are saved
		this.snapshots = originator.doc == null ? [] : [originator.storeFile()];

		// snapshots of state of config file after changes are saved
		this.currSnapshots = [this.snapshots];
	}

	push(memento) {
		if(!(memento instanceof ConfigFileMemento))
			throw new TypeError("Expected a valid configuration file");

		this.snapshots.push(memento);
	}

	/* If there is more than one element in the array,
	 * pop & return the tail of snapshots.
	 *
	 * If there is only one element, don't pop it, just return it */
	pop() {

		if(this.snapshots.length <= 1) {
			return this.snapshots[0];
		}
		
		return this.snapshots.pop();
	}

	getMemento(index) {
		return this.snapshots[index];
	}

	pushToCurr(memento) {
		if(!(memento instanceof ConfigFileMemento))
			throw new TypeError("Expected a valid configuration file");

		this.currSnapshots.push(memento);
	}

	getUndid() {
		return this.currSnapshots[this.currSnapshots.length - 1];
	}
}


export { ConfigFileMemento, ConfigFileOriginator, ConfigFileHistory };
