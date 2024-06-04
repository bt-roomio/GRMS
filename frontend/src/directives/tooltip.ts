const Tooltip = {
    mounted(el: HTMLElement, binding:any) {
        const {x, y, height, width} = el.getBoundingClientRect()
        const { value } = binding
        const tooltipBox = document.createElement('div')
        const tooltip = document.createElement('div')
        tooltip.classList.add('tooltip')
        tooltipBox.classList.add('tooltip__box')
        tooltipBox.innerHTML = value
        tooltip.append(tooltipBox)
        el.addEventListener('mouseenter', () => {
            document.body?.append(tooltip)
            tooltip.style.top = y - (height + 12) + 'px'
            tooltip.style.left = x + (width / 2) + 'px'
            tooltip.style.position = 'fixed'
            tooltip.style.transform = 'translate(-50%, -50%)'
        })
        el.addEventListener('mouseleave', () => {
            tooltip.remove()
        })
    },
    beforeUpdate() {},
    updated() {},
    beforeUnmount() {}, // new
    unmounted() {}
}
export {Tooltip}