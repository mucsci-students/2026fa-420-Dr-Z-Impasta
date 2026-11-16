/*
/Reusable loading bar component that currently takes three parameters
/
/ Label -> a name for the component.
/ Value -> the current value out of the total maximun.
/ Max -> the maximun that the value can be.
*/


export default function LoadingBar({ value, max = 100, label = "Loading" }) {
    return (
        <progress
            className="loading-bar"
            aria-label={label}
            max={max}
            value={Number.isFinite(value) ? value : undefined}
        />
    );
}
