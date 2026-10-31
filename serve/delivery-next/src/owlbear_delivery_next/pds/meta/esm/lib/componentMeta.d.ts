import type { TagName } from '@porsche-design-system/shared';
import type { PropOptions } from '@stencil/core';
export type PropMeta = {
    description?: string;
    type: string;
    defaultValue: boolean | number | string | object | null;
    allowedValues?: 'boolean' | 'number' | 'string' | object | string[] | number[];
    deprecatedValues?: string[];
    isRequired?: boolean;
    isDeprecated?: boolean;
    isExperimental?: boolean;
    isBreakpointCustomizable?: boolean;
    isAria?: boolean;
    isArray?: boolean;
    propOptions?: PropOptions;
};
export type EventMeta = {
    description?: string;
    type: string;
    typeDetail?: string;
    isDeprecated?: boolean;
};
/**
 * @slot Annotation specified in `<component>.tsx`. Documented type includes a `name: string` field which is transformed into key of `slotsMeta`.
 * Metadata defining the relevant slot information in a component.
 */
export type SlotMeta = {
    description?: string;
    isRequired?: boolean;
    allowedTagNames?: (TagName | keyof HTMLElementTagNameMap)[];
    hasAltProp?: boolean;
    isDeprecated?: boolean;
};
/**
 * @controlled Annotation specified in `<component>.tsx`.
 * Metadata defining a relationship between an event and one or more controlled properties in a component.
 */
export type ControlledMeta = {
    props: string[];
    event: string;
    isInternallyMutated?: boolean;
};
/**
 * @css-variable Annotation specified in `<component>.styles.ts`. Documented type includes a `name: string` field which is transformed into key of `cssVariablesMeta`.
 * Metadata defining the relevant slot information in a component.
 */
export type CssVariableMeta = {
    description?: string;
    defaultValue?: string;
    isDeprecated?: boolean;
};
export type ComponentMeta = {
    isDeprecated?: boolean;
    deprecationMessage?: string;
    isExperimental?: boolean;
    isDelegatingFocus: boolean;
    isInternal: boolean;
    isChunked: boolean;
    requiredParent?: TagName | TagName[];
    requiredRootNode?: TagName[];
    requiredChild?: string;
    requiredChildSelector?: string;
    nestedComponents?: TagName[];
    propsMeta?: {
        [propName: string]: PropMeta;
    };
    internalProps?: {
        [propName: string]: boolean | number | string | object | null;
    };
    hostAttributes?: {
        [attrName: string]: string;
    };
    hasSlot: boolean;
    /** Each object key corresponds to a slot. Empty strings as key corresponds to the default slot. Be aware that this is a falsy value in js when working with the keys! */
    slotsMeta?: {
        [slotName: string]: SlotMeta;
    };
    eventsMeta?: {
        [eventName: string]: EventMeta;
    };
    hasEvent: boolean;
    controlledMeta?: ControlledMeta[];
    /** Each object key corresponds to a cssVariable. */
    cssVariablesMeta?: {
        [cssVariableName: string]: CssVariableMeta;
    };
    hasAriaProp: boolean;
    hasObserveAttributes: boolean;
    /**
     * Indicates if a component is form-associated and lets Stencil attach ElementInternals via `@AttachInternals()`.
     * For those components the `attachInternals` API must exist, so consumers have to mock it in test environments.
     *
     * Note: this is deliberately narrower than "uses the ElementInternals API". Components which attach internals
     * manually and defensively (via optional chaining and `try`/`catch`) keep working without the API being available
     * and therefore are not flagged.
     */
    hasElementInternals: boolean;
    observedAttributes?: string[];
    hasObserveChildren: boolean;
    styling: 'jss' | 'scss' | 'hybrid';
};
export type ComponentsMeta = Record<TagName, ComponentMeta>;
export declare const componentMeta: ComponentsMeta;
export declare const getComponentMeta: (component: TagName) => ComponentMeta;
