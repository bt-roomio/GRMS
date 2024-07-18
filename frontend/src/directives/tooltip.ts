import {arrow, offset, autoUpdate, computePosition, Placement, shift} from "@floating-ui/vue";

const Tooltip = {
    mounted(el: HTMLElement, binding: any) {
        const { value } = binding;
        if (value) {
            const floatingEl = document.createElement("div");
            const tooltipBox = document.createElement("div");
            const arrowEl = document.createElement('div');
            floatingEl.classList.add('tooltip')
            tooltipBox.classList.add('tooltip__box')
            arrowEl.classList.add('tooltip__arrow')
            floatingEl.appendChild(arrowEl)
            floatingEl.appendChild(tooltipBox)
            tooltipBox.innerText = value
            const placements: Placement[] = ["top", "right", "bottom", "left"];

            el.addEventListener('mouseenter', async () => {
                document.body.appendChild(floatingEl);
                runFloatingOffset(el, floatingEl, arrowEl, placements[0]);
            });

            el.addEventListener('mouseleave', () => {
                document.body.removeChild(floatingEl);
            });
        }

    },
    beforeUpdate() {},
    updated() {},
    beforeUnmount() {}, // new
    unmounted() {},
};

function runFloatingOffset(el: HTMLElement, floatingEl: HTMLElement, arrowEl: HTMLElement, placement: Placement){
    const arrowLen = arrowEl.offsetWidth;
    const floatingOffset = (Math.sqrt(2 * arrowLen ** 2) / 2);
    autoUpdate(el, floatingEl, () => {
        computePosition(el, floatingEl, {
            placement: placement,
            middleware: [offset(floatingOffset), arrow({ element: arrowEl }), shift({
                padding: 22,
            })]

        }).then(({ x, y, middlewareData, placement }) => {
            Object.assign(floatingEl.style, {
                left: `${x}px`,
                top: `${y}px`
            });

            const side = placement.split("-")[0];
            const staticSide = {
                top: "bottom",
                right: "left",
                bottom: "top",
                left: "right"
            }[side];

            if (middlewareData.arrow) {
                let { x: arrowX, y: arrowY } = middlewareData.arrow;
                const {left} = el.getBoundingClientRect()
                if ((arrowX || 0) < (left - x)){
                    arrowX = (left - x) + arrowLen / 2
                }
                Object.assign(arrowEl.style, {
                    left: arrowX != null ? `${arrowX}px` : "",
                    top: arrowY != null ? `${arrowY}px` : "",
                    [staticSide as string]: `${-arrowLen / 2}px`,
                    transform: "rotate(45deg)",
                });
            }
        });
    });
}

export { Tooltip };
